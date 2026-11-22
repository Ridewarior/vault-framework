"""Exercise observable filesystem and real Git behavior of the optional tool."""

import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import yaml
from urllib.parse import unquote


SOURCE = Path(__file__).resolve().parent.parent
SCRIPT = SOURCE / "tools/vault.py"


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "vault"
        self.root.mkdir()
        self.env = dict(os.environ)
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(key, None)
        cache = str(Path(self.temp.name) / "device")
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        XDG_CACHE_HOME=cache, HOME=cache, USERPROFILE=cache, LOCALAPPDATA=cache)
        self.git("init", "-q")
        self.git("config", "user.name", "Vault test")
        self.git("config", "user.email", "vault-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.config = {"catalog": {}, "timestamps": {"enabled": True}}
        self.save_config()
        for module in SCRIPT.parent.glob("*.py"):
            self.write(f"vault-tools/{module.name}", module.read_text())
        self.write("vault-framework/CATALOG_SCHEMA_VERSION", (SOURCE / "framework/CATALOG_SCHEMA_VERSION").read_text())

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

    def test_native_initial_commit_updates_timestamp(self):
        self.note("home/note.md")
        self.tool("install-hook")
        self.commit()
        committed = self.git("show", "HEAD:home/note.md").stdout
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        self.assertIn("date_updated: " + today, committed)
        self.assertIn("date_created: 2000-01-01", committed)
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
        self.assertIn("Staged description", committed)
        self.assertIn(f"date_updated: {dt.datetime.now(dt.timezone.utc).date()}", committed)

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
        staged = self.git("show", ":home/note.md", env=env).stdout
        self.assertIn(f"date_updated: {dt.datetime.now(dt.timezone.utc).date()}", staged)

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
        self.assertIn(f"date_updated: {dt.datetime.now(dt.timezone.utc).date()}",
                      self.git("show", "HEAD:home/one.md").stdout)

        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout.splitlines(), ["home/two.md"])
        self.assertEqual(self.git("diff", "--name-only").stdout, "")
        self.git("commit", "-qm", "remaining staged work")
        self.assertIn("Other staged description", self.git("show", "HEAD:home/two.md").stdout)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

    def test_hook_write_failure_restores_work_and_staging(self):
        first = self.note("home/first.md")
        last = self.note("home/last.md")
        self.git("add", ".")
        first.write_text(first.read_text() + "Unstaged prose\n")
        original = first.read_bytes()
        before = self.git("write-tree").stdout
        last.chmod(0o444)
        try:
            if os.access(last, os.W_OK):
                self.skipTest("process can write read-only files")
            self.tool("pre-commit", expected=2)
        finally:
            last.chmod(0o644)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(self.git("write-tree").stdout, before)

    def test_locked_index_rolls_back_working_timestamp(self):
        note = self.note("home/n.md")
        self.git("add", ".")
        local = note.read_bytes() + b"Unstaged prose\n"
        note.write_bytes(local)
        index_tree = self.git("write-tree").stdout
        lock = self.write(".git/index.lock", "held")
        try:
            self.tool("pre-commit", expected=2)
        finally:
            lock.unlink()
        self.assertEqual(self.git("write-tree").stdout, index_tree)
        self.assertEqual(note.read_bytes(), local)

    def test_timestamp_scalar_styles_preserve_surrounding_yaml(self):
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        for i, field in enumerate((
            '"date_updated": "2001-01-01" # keep',
            "'date_updated': |- # keep\n  2001-01-01",
            "date_updated: > # keep\n  2001-01-01",
        )):
            note = self.note(f"home/n{i}.md")
            note.write_text(note.read_text().replace("date_updated: 2001-01-01", field))
            original = note.read_text()
            self.git("add", ".")
            self.tool("pre-commit")
            self.assertEqual(note.read_text(), original.replace("2001-01-01", today))
            self.assertEqual(str(yaml.safe_load(note.read_text().split("---")[1])["date_updated"]).strip(), today)

    def test_custom_post_commit_hook_preserved_before_installing_either_hook(self):
        post = self.write(".git/hooks/post-commit", "#!/bin/sh\n# custom post hook\n")
        self.tool("install-hook", expected=2)
        self.assertIn("custom post hook", post.read_text())
        self.assertFalse((post.parent / "pre-commit").exists())

    def test_ambiguous_timestamp_alias_does_not_modify_its_source(self):
        path = self.note("home/n.md")
        path.write_text(path.read_text().replace("date_created: 2000-01-01", "date_created: &original 2000-01-01")
                        .replace("date_updated: 2001-01-01", 'date_updated: *original'))
        self.git("add", ".")
        before = self.git("write-tree").stdout
        original = path.read_bytes()
        self.assertIn("direct scalar", self.tool("pre-commit", expected=2).stderr)
        self.assertEqual(self.git("write-tree").stdout, before)
        self.assertEqual(original, path.read_bytes())

    def test_existing_hook_is_preserved(self):
        hook = self.write(".git/hooks/pre-commit", "#!/bin/sh\n# existing custom hook\n")
        self.tool("install-hook", expected=2)
        self.assertIn("existing custom hook", hook.read_text())

    def test_staged_config_wins_over_unstaged_config_edits(self):
        self.note("home/note.md")
        self.git("add", ".")
        self.config["timestamps"]["enabled"] = False
        self.save_config()
        self.tool("install-hook")
        self.git("commit", "-qm", "staged config")
        committed = self.git("show", "HEAD:home/note.md").stdout
        self.assertIn(f"date_updated: {dt.datetime.now(dt.timezone.utc).date()}", committed)
        self.assertFalse(json.loads((self.root / "vault.config.json").read_text())["timestamps"]["enabled"])

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

    def test_timestamp_hook_refuses_symlinked_working_notes(self):
        note = self.note("home/note.md")
        self.git("add", ".")
        authored = self.write("authored.md", "Keep this content\n")
        note.unlink()
        note.symlink_to(authored)
        result = self.tool("pre-commit", expected=2)
        self.assertIn("symlinked", result.stderr)
        self.assertEqual(authored.read_text(), "Keep this content\n")
        self.assertIn("date_updated: 2001-01-01", self.git("show", ":home/note.md").stdout)

    def test_manually_assembled_vault_links_and_tooling(self):
        for obsidian in (False, True):
            target = Path(self.temp.name) / ("with-editor" if obsidian else "plain")
            (target / "vault-tools").mkdir(parents=True)
            shutil.copytree(SOURCE / "starter/inbox", target / "inbox")
            for name in ("AGENTS.md", "README.md", "vault.config.json"):
                shutil.copy2(SOURCE / "starter" / name, target / name)
            shutil.copytree(SOURCE / "starter/templates", target / "templates")
            shutil.copytree(SOURCE / "starter/guidelines", target / "guidelines")
            shutil.copytree(SOURCE / "framework", target / "vault-framework")
            self.assertEqual((target / "vault-framework/VERSION").read_bytes(), (SOURCE / "framework/VERSION").read_bytes())
            shutil.copytree(SOURCE / "tools", target / "vault-tools", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
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
            result = json.loads(self.run_process([*command, "sync"]).stdout)
            self.run_process([*command, "install-hook"])
            with sqlite3.connect(result["database"]) as db:
                found = db.execute("SELECT description FROM notes WHERE path = 'home/note.md'").fetchone()
            self.assertEqual(found, ("Manual setup example",))
            self.assertFalse((target / "home/index.md").exists())
            self.assertTrue((target / ".git/hooks/pre-commit").is_file())
            self.assertEqual((target / ".obsidian").exists(), obsidian)

    def test_catalog_hook_reads_working_tree_and_preserves_staged_timestamps(self):
        self.tool("install-hook")
        self.note("home/note.md", body="committedtext")
        self.write("home/index.md", "# Authored navigation\n")
        self.git("add", ".")
        self.note("home/note.md", body="workingtext")
        self.write("inbox/new.md", "# Untracked capture\n")
        self.git("commit", "-qm", "Catalog from the working tree")
        committed = self.git("show", "HEAD:home/note.md").stdout
        self.assertIn("committedtext", committed)
        self.assertNotIn("workingtext", committed)
        self.assertIn(f"date_updated: {dt.datetime.now(dt.timezone.utc).date()}", committed)
        result = json.loads(self.tool("sync").stdout)
        self.assertEqual((result["added"], result["updated"], result["removed"]), (0, 0, 0))
        with sqlite3.connect(result["database"]) as db:
            self.assertEqual(db.execute("SELECT path FROM note_text WHERE note_text MATCH 'workingtext'").fetchall(),
                             [("home/note.md",)])
            self.assertEqual(db.execute("SELECT path FROM notes ORDER BY path").fetchall(),
                             [("home/index.md",), ("home/note.md",), ("inbox/new.md",)])
        self.assertEqual((self.root / "home/index.md").read_text(), "# Authored navigation\n")

    def test_catalog_hook_failure_does_not_reject_commit(self):
        self.tool("install-hook")
        self.note("home/note.md")
        self.git("add", ".")
        self.write("vault.config.json", "{ unfinished")
        result = self.git("commit", "-qm", "Valid staged config")
        self.assertIn("Catalog sync failed", result.stderr)
        self.assertIn("No previous snapshot", result.stderr)
        self.assertIn("Valid staged config", self.git("log", "-1", "--format=%s").stdout)


if __name__ == "__main__":
    unittest.main()
