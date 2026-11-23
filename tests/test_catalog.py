"""Check catalog discovery, incremental updates and failure recovery."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE / "tools"))
import catalog
from vault import sync_catalog
sys.path.pop(0)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.root = self.base / "vault"
        self.root.mkdir()
        cache = str(self.base / "device")
        env = patch.dict(os.environ, XDG_CACHE_HOME=cache, HOME=cache,
                         USERPROFILE=cache, LOCALAPPDATA=cache)
        env.start()
        self.addCleanup(env.stop)
        self.database = catalog.database_path(self.root)

    def write(self, path, content):
        path = self.root / path
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return path

    def sync(self):
        return sync_catalog(self.root)

    def query(self, sql, *args):
        with closing(sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)) as db:
            return db.execute(sql, args).fetchall()

    def match(self, query):
        return self.query("SELECT path FROM note_text WHERE note_text MATCH ? ORDER BY path", query)

    def test_saved_working_files_and_scope_without_git(self):
        self.write("inbox/quick.md", "# Raw capture\nA rough idea about returns.")
        self.write("engineering/thought.md", "---\ntags: [thought-bubbles, work/design]\n---\nTry this idea.")
        self.write("engineering/README.md", "# Authored subject guide")
        self.write("engineering/index.md", "# Authored navigation")
        self.write("root.MD", "A root note.")
        self.write("engineering/design.md", """---
title: Next iteration
description: Checkout response
ticket_id: "0042"
date_created: 2026-10-01
tags: [work, work/feature, workshop, work/feature]
extra:
  custom: true
---
# Body title
""")
        for path in ("AGENTS.md", ".hidden/note.md", "engineering/.private.md", "vault-tools/README.md",
                     "templates/note.md", "attachments/note.md", "guidelines/README.md",
                     "engineering/guidelines/README.md", "vault-framework/README.md"):
            self.write(path, "Scope exclusion.")
        if os.name != "nt":
            (self.root / "engineering/link.md").symlink_to(self.root / "root.MD")
            os.mkfifo(self.root / "engineering/pipe.md")
        result = self.sync()
        self.assertEqual((result["added"], result["coverage"]), (6, []))
        self.assertFalse(self.database.is_relative_to(self.root))
        self.assertEqual(self.query("PRAGMA user_version"), [(1,)])
        self.assertEqual(self.match("returns"), [("inbox/quick.md",)])
        self.assertEqual(self.match("iteration AND checkout"), [("engineering/design.md",)])
        self.assertEqual(self.query(
            """SELECT DISTINCT path FROM tags
            WHERE tag = ? OR substr(tag, 1, length(?) + 1) = ? || '/'
            ORDER BY path""", "work", "work", "work",
        ), [("engineering/design.md",), ("engineering/thought.md",)])
        self.assertEqual(self.query(
            "SELECT subject, title, date_created, json_extract(metadata_json, '$.extra.custom')"
            " FROM notes WHERE ticket_id = ?", "0042",
        ), [("engineering", "Next iteration", "2026-10-01", 1)])
        self.assertEqual(self.query("SELECT metadata_json FROM notes WHERE path = 'root.MD'"), [("{}",)])
        self.assertIn(("engineering/index.md",), self.match("navigation"))

    def test_incremental_edits_moves_and_deletions(self):
        first = self.write("subject/old.md", "---\ntags: [old/tag]\ncustom: one\n---\nfirstword")
        self.write("extra/delete.md", "deleteword")
        self.assertEqual(self.sync()["added"], 2)
        before = self.database.stat().st_mtime_ns
        self.assertEqual((self.sync()["updated"], self.database.stat().st_mtime_ns), (0, before))
        first.write_text("---\ntags: [new/tag]\ncustom: two\n---\nsecondword")
        self.assertEqual(self.sync()["updated"], 1)
        self.assertEqual(self.match("firstword"), [])
        self.assertEqual(self.query("SELECT tag FROM tags"), [("new/tag",)])
        first.write_text("---\ntags: [new/tag]\ncustom: three\n---\nthirdword")
        self.assertEqual(self.sync()["updated"], 1)
        (self.root / "subject").rename(self.root / "moved")
        (self.root / "extra/delete.md").unlink()
        self.write("inbox/new.md", "new capture")
        result = self.sync()
        self.assertEqual((result["added"], result["updated"], result["removed"]), (2, 0, 2))
        self.assertEqual(self.match("thirdword"), [("moved/old.md",)])

    def test_draft_generated_index_is_skipped_and_authored_index_is_searchable(self):
        index = self.write("subject/index.md", "# Authored navigation")
        self.assertEqual(self.sync()["added"], 1)
        generated = b"<!-- vault-framework: generated index -->\r\n# Old navigation"
        index.write_bytes(generated)
        self.assertEqual(self.sync()["removed"], 1)
        self.assertEqual(self.sync()["removed"], 0)
        self.assertEqual(index.read_bytes(), generated)
        index.write_text("# New navigation")
        self.assertEqual(self.sync()["added"], 1)
        self.assertEqual(self.match("navigation"), [("subject/index.md",)])

    def test_local_properties_keep_types_and_repeated_list_positions(self):
        self.write("local.md", "---\nrelated_tickets: [A, B, A]\nvalues: [true, 1, '1', null]\nempty: []\n---\n")
        self.sync()
        self.assertEqual(self.query(
            "SELECT position FROM properties WHERE name='related_tickets' AND value_json=json_quote(?) ORDER BY position", "A"
        ), [(0,), (2,)])
        self.assertEqual(self.query(
            "SELECT value_json FROM properties WHERE name='values' ORDER BY position"
        ), [('true',), ('1',), ('"1"',), ('null',)])
        self.assertEqual(self.query("SELECT json_type(metadata_json, '$.empty') FROM notes"), [('array',)])

    def test_invalid_metadata_remains_searchable_and_restores(self):
        first = self.write("one.md", "---\ntags: [work]\n---\n# Valid")
        self.sync()
        first.write_text("--- \ntags: [unfinished\nCurrent readable body")
        result = self.sync()
        self.assertEqual([(g["path"], g["kind"]) for g in result["coverage"]], [("one.md", "metadata")])
        self.assertEqual(self.sync()["coverage"], result["coverage"])
        self.assertEqual(self.match("readable"), [("one.md",)])
        self.assertEqual(self.query("SELECT metadata_json FROM notes"), [(None,)])
        self.assertEqual(self.query("SELECT tag FROM tags"), [])
        first.write_text("---\ntags: [work/feature]\n---\n# Restored")
        self.assertEqual(self.sync()["coverage"], [])
        self.assertEqual(self.query("SELECT tag FROM tags"), [("work/feature",)])
        self.assertEqual(self.query("SELECT * FROM coverage"), [])

    def test_unfinished_explicit_yaml_types_do_not_block_other_notes(self):
        self.write("healthy.md", "new text")
        for name, value in (("date", "!!timestamp tomorrow"), ("flag", "!!bool maybe")):
            self.write(name + ".md", f"---\nreviewed: {value}\n---\nRecoverable draft")
        result = self.sync()
        self.assertEqual(result["added"], 3)
        self.assertEqual([(g["path"], g["kind"]) for g in result["coverage"]],
                         [("date.md", "metadata"), ("flag.md", "metadata")])
        self.assertEqual(self.match("recoverable"), [("date.md",), ("flag.md",)])

    def test_case_only_directory_move_uses_actual_spelling(self):
        self.write("Subject/note.md", "new spelling")
        self.sync()
        (self.root / "Subject").rename(self.root / "temp")
        (self.root / "temp").rename(self.root / "subject")
        old = self.root / "Subject/note.md"
        actual = self.root / "subject/note.md"
        lstat = Path.lstat
        # On a case-insensitive volume the retired spelling still resolves.
        def case_insensitive_lstat(path):
            return lstat(actual if str(path) == str(old) else path)
        with patch.object(Path, "lstat", case_insensitive_lstat):
            result = self.sync()
        self.assertEqual((result["added"], result["removed"], result["coverage"]), (1, 1, []))
        self.assertEqual(self.match("spelling"), [("subject/note.md",)])

    def test_interrupted_sqlite_writer_recovers_on_next_sync(self):
        self.write("one.md", "original")
        self.sync()
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("CREATE TABLE padding(data BLOB)")
            db.executemany("INSERT INTO padding VALUES (zeroblob(8192))", [()] * 30)
        # Force changed pages onto disk, then terminate without rollback or close.
        subprocess.run([sys.executable, "-c", """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.execute('PRAGMA cache_size=2')
db.execute('UPDATE padding SET data=randomblob(8192)')
os._exit(0)
""", str(self.database)], check=True)
        self.assertTrue(Path(str(self.database) + "-journal").exists())
        self.write("one.md", "afterrecovery")
        self.assertEqual(self.sync()["updated"], 1)
        self.assertEqual(self.match("afterrecovery"), [("one.md",)])
        self.assertEqual(self.query("SELECT count(*) FROM padding WHERE data=zeroblob(8192)"), [(30,)])

    def test_sync_reports_prepared_reader_outside_path(self):
        self.write(".venv/vault-sqlite3", sys.executable + "\n")
        with patch.dict(os.environ, PATH=""):
            self.assertEqual(self.sync()["sqlite3"], sys.executable)

    def test_inaccessible_subtree_and_unreadable_text_are_retried(self):
        folder = self.write("subject/note.md", "old searchable text").parent
        self.write("bad.md", b"\xff")
        self.sync()
        (folder / "note.md").unlink()
        scandir = os.scandir

        def deny(path):
            if path == folder:
                raise PermissionError("vault subject is inaccessible")
            return scandir(path)

        with patch.object(catalog.os, "scandir", side_effect=deny):
            result = self.sync()
        self.assertEqual(result["removed"], 0)
        self.assertEqual([(g["path"], g["kind"]) for g in result["coverage"]],
                         [("bad.md", "scan"), ("subject", "scan")])
        self.assertEqual(self.match("searchable"), [("subject/note.md",)])
        self.write("bad.md", "readable again")
        result = self.sync()
        self.assertEqual((result["added"], result["removed"], result["coverage"]), (1, 1, []))

    def test_scan_gap_clears_back_to_same_metadata_gap(self):
        path = self.write("subject/note.md", "---\ntags: [unfinished\nSearchable body")
        first = self.sync()
        self.assertEqual(first["coverage"][0]["kind"], "metadata")
        read = catalog.read_saved

        def deny(note):
            if note == path:
                raise PermissionError("vault note is inaccessible")
            return read(note)

        with patch.object(catalog, "read_saved", side_effect=deny):
            self.assertEqual(self.sync()["coverage"][0]["kind"], "scan")
        restored = self.sync()
        self.assertEqual(restored["updated"], 0)
        self.assertEqual(restored["coverage"], first["coverage"])

    def test_unavailable_vault_reports_previous_snapshot(self):
        self.write("note.md", "old searchable text")
        self.sync()
        self.root.rename(self.base / "offline")
        with self.assertRaisesRegex(Exception, "A previous snapshot is available"):
            self.sync()
        self.assertEqual(self.match("searchable"), [("note.md",)])

    def test_old_schema_is_rebuilt_only_on_success_and_newer_is_untouched(self):
        self.database.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("CREATE VIRTUAL TABLE legacy USING fts5(body)")
            db.execute("INSERT INTO legacy VALUES ('previous')")
        self.write("note.md", b"\xff")
        with self.assertRaisesRegex(Exception, "Cannot rebuild the older catalog.*A previous snapshot"):
            self.sync()
        self.assertEqual(self.query("SELECT body FROM legacy"), [("previous",)])
        self.assertEqual(self.query("PRAGMA user_version"), [(0,)])
        self.write("note.md", "new snapshot")
        self.assertEqual(self.sync()["added"], 1)
        self.assertEqual(self.query("SELECT name FROM sqlite_master WHERE name LIKE 'legacy%'"), [])
        self.assertEqual(self.query("PRAGMA user_version"), [(1,)])
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("PRAGMA user_version = 2")
        before = self.database.read_bytes()
        with self.assertRaisesRegex(Exception, "schema 2 is newer"):
            self.sync()
        self.assertEqual(self.database.read_bytes(), before)

    def test_tools_and_framework_must_agree_before_sync(self):
        self.sync()
        before = self.database.read_bytes()
        (self.root / "vault-framework").mkdir()
        self.write("vault-framework/CATALOG_SCHEMA_VERSION", "2\n")
        with patch.object(catalog, "__file__", str(self.root / "vault-tools/catalog.py")):
            with self.assertRaisesRegex(Exception, "framework declares schema 2"):
                self.sync()
        self.assertEqual(self.database.read_bytes(), before)

    def test_cli_and_concurrent_refreshes_share_one_snapshot(self):
        self.write("a.md", "a new note")
        script = [sys.executable, str(SOURCE / "tools/vault.py"), "--vault", str(self.root), "sync"]
        children = [subprocess.Popen(script, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    for _ in range(2)]
        results = []
        for child in children:
            out, err = child.communicate(timeout=20)
            self.assertEqual(child.returncode, 0, out + err)
            results.append(json.loads(out))
        self.assertEqual(sorted(result["added"] for result in results), [0, 1])
        self.assertEqual({result["database"] for result in results}, {str(self.database)})
        self.assertEqual(self.match("new"), [("a.md",)])
