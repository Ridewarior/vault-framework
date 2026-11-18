"""Exercise observable filesystem and real Git behavior of the optional tool."""

import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote


SOURCE = Path(__file__).resolve().parent.parent
SCRIPT = SOURCE / "vault-tools/vault.py"


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "vault"
        self.root.mkdir()
        self.env = dict(os.environ)
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(key, None)
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q")
        self.git("config", "user.name", "Vault test")
        self.git("config", "user.email", "vault-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.config = {"indexes": {}, "timestamps": {"enabled": True}}
        self.save_config()
        self.write("vault-tools/vault.py", SCRIPT.read_text())

    def run_process(self, args, *, expected=0, env=None):
        result = subprocess.run(args, cwd=self.root, env=env or self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def git(self, *args, expected=0, env=None):
        return self.run_process(["git", *args], expected=expected, env=env)

    def tool(self, *args, expected=0, env=None):
        return self.run_process([sys.executable, str(self.root / "vault-tools/vault.py"), *args], expected=expected, env=env)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def save_config(self):
        self.write("vault.config.json", json.dumps(self.config))

    def note(self, path, *, tags=None, description="Staged description", extra="", body="Original body"):
        content = "---\ntags: " + json.dumps(tags or ["resource"]) + "\n"
        content += "description: " + json.dumps(description) + "\n"
        content += "date_created: 2000-01-01\ndate_updated: 2001-01-01\n" + extra
        return self.write(path, content + "---\n\n# Example\n\n" + body + "\n")

    def commit(self, message="fixture"):
        self.git("add", ".")
        self.git("commit", "-qm", message)

    def test_recursive_groups_paths_and_configurable_fields(self):
        self.config["indexes"].update(properties=["description", "ticket_id", "tags"], display_tags=["work"])
        self.save_config()
        self.note("engineering/root.md")
        self.note("engineering/deep/work/ticket one.md", tags=["work/bug", "subject"], description="A | B", extra="ticket_id: ABC-42\n")
        self.tool("index")
        output = (self.root / "engineering/index.md").read_text()
        self.assertIn("## .", output)
        self.assertIn("## deep/work", output)
        self.assertIn("deep/work/ticket%20one.md", output)
        self.assertIn("deep/work/ticket one.md", output)
        self.assertIn("A \\| B", output)
        self.assertIn("ABC-42 | work/bug", output)
        self.assertNotIn("subject", output)

    def test_filters_exemptions_and_nested_scope_guidelines(self):
        self.config["indexes"].update(include_tags=["work"], exclude_properties={"status": "done"})
        self.save_config()
        self.note("engineering/work/active.md", tags=["work/docs"])
        self.note("engineering/guidelines/policy.md", tags=["work/docs"])
        self.note("engineering/finished.md", tags=["work/bug"], extra="status: done\n")
        self.note("engineering/other.md")
        self.write("engineering/bubble.md", "---\ntags: [thought-bubbles]\n---\nrough")
        self.write("inbox/raw.md", "unstructured capture")
        self.tool("index")
        output = (self.root / "engineering/index.md").read_text()
        self.assertIn("work/active.md", output)
        for omitted in ("guidelines/policy.md", "finished.md", "other.md", "bubble.md"):
            self.assertNotIn(omitted, output)
        self.assertFalse((self.root / "inbox/index.md").exists())

    def test_check_and_regeneration_are_idempotent(self):
        self.note("home/note.md")
        self.tool("index", "--check", expected=1)
        self.assertFalse((self.root / "home/index.md").exists())
        self.tool("index")
        target = self.root / "home/index.md"
        modified = target.stat().st_mtime_ns
        self.tool("index")
        self.assertEqual(target.stat().st_mtime_ns, modified)
        self.tool("index", "--check")

    def test_framework_copy_is_never_indexed_or_modified(self):
        self.config["indexes"]["exclude_paths"] = []
        self.save_config()
        framework = self.write("vault-framework/README.md", "# Framework copy\n\nLeave this unchanged.\n")
        original = framework.read_bytes()
        self.note("home/note.md")
        self.tool("index")
        self.assertEqual(framework.read_bytes(), original)
        self.assertFalse((self.root / "vault-framework/index.md").exists())
        self.assertTrue((self.root / "home/index.md").exists())

    def test_scoped_guidelines_do_not_require_note_metadata(self):
        self.config["indexes"]["exclude_paths"] = []
        self.save_config()
        self.write("engineering/guidelines/README.md", "# Scope guidance\n")
        self.write("engineering/service/guidelines/tags.md", "# Nested scope tags\n")
        self.note("engineering/reference.md")
        self.tool("index")
        output = (self.root / "engineering/index.md").read_text()
        self.assertIn("reference.md", output)
        self.assertNotIn("guidelines/", output)

    def test_index_generation_without_git(self):
        plain = Path(self.temp.name) / "plain-vault"
        (plain / "home").mkdir(parents=True)
        (plain / "vault.config.json").write_text(json.dumps(self.config))
        (plain / "home/note.md").write_text("---\ntags: [resource]\ndescription: A note in ordinary storage\n---\n# Example\n")
        command = [sys.executable, str(SCRIPT), "--vault", str(plain)]
        self.run_process([*command, "index"])
        self.run_process([*command, "index", "--check"])
        self.assertIn("ordinary storage", (plain / "home/index.md").read_text())
        self.assertFalse((plain / ".git").exists())

    def test_bad_metadata_does_not_partially_write_outputs(self):
        self.note("a/good.md")
        self.write("b/bad.md", "---\ntags: [resource]\n---\n# No description\n")
        self.tool("index", expected=2)
        self.assertFalse((self.root / "a/index.md").exists())
        self.write("b/bad.md", "---\ntags: [resource]\ntags: [work]\n---\n")
        self.assertIn("unique", self.tool("index", expected=2).stderr)

    def test_authored_index_is_preserved(self):
        self.note("home/note.md")
        target = self.write("home/index.md", "# My authored navigation\n")
        self.tool("index", expected=2)
        self.assertEqual(target.read_text(), "# My authored navigation\n")

    def test_native_initial_commit_creates_index_and_timestamps(self):
        self.note("home/note.md")
        self.tool("install-hook")
        self.commit()
        committed = self.git("show", "HEAD:home/note.md").stdout
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        self.assertIn("date_updated: " + today, committed)
        self.assertIn("date_created: 2000-01-01", committed)
        self.assertIn("note.md", self.git("show", "HEAD:home/index.md").stdout)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

    def test_partial_staging_preserves_unstaged_description_and_body(self):
        note = self.note("home/note.md")
        self.commit()
        self.tool("install-hook")
        staged = note.read_text().replace("Original body", "Staged body")
        note.write_text(staged)
        self.git("add", "home/note.md")
        note.write_text(staged.replace("Staged description", "Unstaged description") + "Unstaged prose\n")
        self.git("commit", "-qm", "partial")
        committed = self.git("show", "HEAD:home/note.md").stdout
        self.assertIn("Staged body", committed)
        self.assertNotIn("Unstaged", committed)
        self.assertIn("Unstaged description", note.read_text())
        self.assertIn("Unstaged prose", note.read_text())
        self.assertIn("date_created: 2000-01-01", note.read_text())
        self.assertIn("Staged description", self.git("show", "HEAD:home/index.md").stdout)
        self.assertNotIn("Unstaged description", self.git("show", "HEAD:home/index.md").stdout)

    def test_untracked_notes_do_not_leak_into_commit_indexes(self):
        self.note("home/tracked.md")
        self.git("add", ".")
        self.note("home/untracked.md")
        self.tool("install-hook")
        self.git("commit", "-qm", "tracked only")
        self.assertNotIn("untracked.md", self.git("show", "HEAD:home/index.md").stdout)
        self.assertTrue((self.root / "home/untracked.md").exists())

    def test_staged_deletion_removes_index_entry(self):
        self.note("home/keep.md")
        self.note("home/remove.md")
        self.tool("install-hook")
        self.commit()
        self.git("rm", "home/remove.md")
        self.git("commit", "-qm", "remove")
        output = self.git("show", "HEAD:home/index.md").stdout
        self.assertIn("keep.md", output)
        self.assertNotIn("remove.md", output)
        self.assertNotIn("](index.md)", output)

    def test_unstaged_index_edits_abort_before_mutating_staging(self):
        note = self.note("home/note.md")
        self.tool("index")
        self.commit()
        self.tool("install-hook")
        note.write_text(note.read_text() + "Staged change\n")
        self.git("add", "home/note.md")
        index = self.root / "home/index.md"
        index.write_text(index.read_text() + "Unstaged index notes\n")
        # Change metadata so the hook must regenerate the index.
        note.write_text(note.read_text().replace("Staged description", "New description"))
        self.git("add", "home/note.md")
        original_staged = self.git("show", ":home/note.md").stdout
        self.git("commit", "-qm", "should fail", expected=1)
        self.assertEqual(self.git("show", ":home/note.md").stdout, original_staged)
        self.assertIn("Unstaged index notes", index.read_text())

    def test_timestamp_only_changes_are_not_overridden(self):
        note = self.note("home/note.md")
        self.commit()
        self.tool("install-hook")
        note.write_text(note.read_text().replace("date_updated: 2001-01-01", "date_updated: 2002-02-02"))
        self.git("add", "home/note.md")
        self.git("commit", "-qm", "date only")
        self.assertIn("date_updated: 2002-02-02", self.git("show", "HEAD:home/note.md").stdout)

    def test_alternate_git_index_is_respected(self):
        note = self.note("home/note.md")
        self.commit()
        normal = self.git("show", ":home/note.md").stdout
        alternate = Path(self.temp.name) / "alternate-index"
        shutil.copy2(self.root / ".git/index", alternate)
        env = {**self.env, "GIT_INDEX_FILE": str(alternate)}
        note.write_text(note.read_text() + "Alternate staged change\n")
        self.git("add", "home/note.md", env=env)
        self.tool("pre-commit", env=env)
        self.assertEqual(self.git("show", ":home/note.md").stdout, normal)
        self.assertIn("Alternate staged change", self.git("show", ":home/note.md", env=env).stdout)
        self.assertIn("home/index.md", self.git("ls-files", env=env).stdout)

    def test_explicit_path_commit_excludes_other_staged_changes(self):
        one = self.note("home/one.md")
        two = self.note("home/two.md")
        self.commit()
        self.tool("install-hook")
        one.write_text(one.read_text().replace("Staged description", "Selected description"))
        two.write_text(two.read_text().replace("Staged description", "Other staged description"))
        self.git("add", "home/two.md")
        self.git("commit", "-qm", "one file", "home/one.md")
        self.assertIn("Selected description", self.git("show", "HEAD:home/one.md").stdout)
        self.assertNotIn("Other staged description", self.git("show", "HEAD:home/two.md").stdout)
        index = self.git("show", "HEAD:home/index.md").stdout
        self.assertIn("Selected description", index)
        self.assertNotIn("Other staged description", index)

    def test_existing_hook_is_preserved(self):
        hook = self.write(".git/hooks/pre-commit", "#!/bin/sh\n# existing custom hook\n")
        self.tool("install-hook", expected=2)
        self.assertIn("existing custom hook", hook.read_text())

    def test_staged_config_wins_over_unstaged_config_edits(self):
        self.note("home/note.md")
        self.git("add", ".")
        self.config["indexes"]["exclude_paths"] = ["home"]
        self.save_config()
        self.tool("install-hook")
        self.git("commit", "-qm", "staged config")
        self.assertIn("note.md", self.git("show", "HEAD:home/index.md").stdout)
        self.assertIn('"home"', (self.root / "vault.config.json").read_text())

    def test_timestamp_opt_in_and_disabled_setting(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                self.config["timestamps"]["enabled"] = enabled
                self.save_config()
                note = self.note("home/note.md")
                if enabled:
                    note.write_text(note.read_text().replace("date_updated: 2001-01-01\n", ""))
                self.git("add", ".")
                self.tool("pre-commit")
                staged = self.git("show", ":home/note.md").stdout
                self.assertIn("date_created: 2000-01-01", staged)
                if enabled:
                    self.assertNotIn("date_updated", staged)
                else:
                    self.assertIn("date_updated: 2001-01-01", staged)

    def test_bad_date_and_symlinked_output_fail_without_overwriting(self):
        self.note("home/note.md", extra="invalid_date: 2026-99-99\n")
        self.assertNotIn("Traceback", self.tool("index", expected=2).stderr)
        self.note("home/note.md")
        authored = self.write("authored.md", "Keep this content\n")
        (self.root / "home/index.md").symlink_to(authored)
        self.tool("index", expected=2)
        self.assertEqual(authored.read_text(), "Keep this content\n")

    def test_manually_assembled_vault_links_and_tooling(self):
        for obsidian in (False, True):
            target = Path(self.temp.name) / ("with-editor" if obsidian else "plain")
            (target / "vault-tools").mkdir(parents=True)
            shutil.copytree(SOURCE / "starter/inbox", target / "inbox")
            for name in ("AGENTS.md", "README.md", "vault.config.json"):
                shutil.copy2(SOURCE / "starter" / name, target / name)
            shutil.copytree(SOURCE / "starter/templates", target / "templates")
            shutil.copytree(SOURCE / "starter/guidelines", target / "guidelines")
            shutil.copytree(SOURCE / "vault-framework", target / "vault-framework")
            self.assertEqual((target / "vault-framework/VERSION").read_bytes(), (SOURCE / "vault-framework/VERSION").read_bytes())
            for name in ("vault.py", "requirements.txt", "README.md"):
                shutil.copy2(SOURCE / "vault-tools" / name, target / "vault-tools" / name)
            for name in (".gitignore", ".gitattributes"):
                shutil.copy2(SOURCE / name, target / name)
            if obsidian:
                shutil.copytree(SOURCE / "starter/.obsidian", target / ".obsidian")
            self.git("-C", str(target), "init", "-q")
            for path in target.rglob("*.md"):
                visible = re.sub(r"^```.*?^```[^\n]*", "", path.read_text(), flags=re.M | re.S)
                for link in re.findall(r"\]\(([^)]+)\)", visible):
                    if "://" not in link and not link.startswith("#"):
                        self.assertTrue((path.parent / unquote(link.split("#")[0])).exists(), f"{path}: {link}")
            (target / "home").mkdir()
            (target / "home/note.md").write_text("---\ntags: [resource]\ndescription: Manual setup example\n---\n# Example\n")
            command = [sys.executable, str(target / "vault-tools/vault.py"), "--vault", str(target)]
            self.run_process([*command, "index"])
            self.run_process([*command, "install-hook"])
            self.assertIn("Manual setup example", (target / "home/index.md").read_text())
            self.assertTrue((target / ".git/hooks/pre-commit").is_file())
            self.assertEqual((target / ".obsidian").exists(), obsidian)


if __name__ == "__main__":
    unittest.main()
