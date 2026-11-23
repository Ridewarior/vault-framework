"""Refresh the device-local SQLite catalog from saved Markdown."""

from contextlib import closing
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import sys

from vault_notes import VaultError, canonical, excluded, metadata, text


INDEX_MARKER = b"<!-- vault-framework: generated index -->"
SUPPORTED_SCHEMA_VERSION = 1
SCHEMA = (
    """CREATE TABLE notes (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE NOT NULL,
        subject TEXT,
        title TEXT NOT NULL,
        description TEXT,
        date_created TEXT,
        date_updated TEXT,
        ticket_id TEXT,
        metadata_json TEXT,
        content_hash TEXT NOT NULL
    )""",
    """CREATE TABLE properties (
        path TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE,
        name TEXT NOT NULL,
        position INTEGER NOT NULL,
        value_json TEXT NOT NULL,
        PRIMARY KEY (path, name, position)
    )""",
    "CREATE INDEX properties_by_value ON properties(name, value_json, path)",
    """CREATE VIEW tags AS SELECT DISTINCT path, json_extract(value_json, '$') AS tag
       FROM properties WHERE name = 'tags'""",
    "CREATE INDEX notes_by_ticket ON notes(ticket_id)",
    "CREATE VIRTUAL TABLE note_text USING fts5(path, title, description, body)",
    """CREATE TABLE coverage (
        path TEXT PRIMARY KEY NOT NULL,
        kind TEXT NOT NULL,
        detail TEXT NOT NULL
    )""",
)


def database_path(root):
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData/Local")
    elif sys.platform == "darwin":
        base = home / "Library/Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
        if not base.is_absolute():
            base = home / ".cache"
    key = hashlib.sha256(os.fsencode(os.path.normcase(root))).hexdigest()
    path = base / "vault-framework" / "catalogs" / key / "catalog.sqlite"
    resolved = path.resolve()
    if not base.is_absolute() or path.parent.resolve().is_relative_to(root) or resolved.is_relative_to(root):
        raise VaultError("The catalog cache must be outside the vault")
    if path.is_symlink() or path.parent.is_symlink():
        raise VaultError("The catalog cache cannot use a symlink for the database or its directory")
    return path


def version(db):
    return db.execute("PRAGMA user_version").fetchone()[0]


def schema_version():
    # Read the installed release declaration, or the one in a source checkout.
    tools = Path(__file__).resolve().parent
    framework = "vault-framework" if tools.name == "vault-tools" else "framework"
    declaration = tools.parent / framework / "CATALOG_SCHEMA_VERSION"
    value = declaration.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[1-9][0-9]*", value) or int(value) > 2147483647:
        raise VaultError(f"{declaration}: expected a positive SQLite schema version")
    if int(value) != SUPPORTED_SCHEMA_VERSION:
        raise VaultError(f"The framework declares schema {value}, but these tools implement "
                        f"schema {SUPPORTED_SCHEMA_VERSION}. Update the framework and tools together")
    return SUPPORTED_SCHEMA_VERSION


def check_version(found, supported):
    if found > supported:
        raise VaultError(f"Catalog schema {found} is newer than this framework supports ({supported}). Update the framework and tools")


def snapshot_status(database):
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
            tables = db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' LIMIT 1")
            if tables.fetchone():
                return f"A previous snapshot is available at {database} (schema {version(db)})."
    except sqlite3.Error:
        if database.exists():
            return f"Could not verify a previous snapshot at {database}."
    return "No previous snapshot is available."


def signature(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_saved(path):
    for _ in range(2):
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            flags |= getattr(os, "O_BINARY", 0)
            with os.fdopen(os.open(path, flags), "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise VaultError("Expected a regular file")
                data = stream.read()
                seen = signature(os.fstat(stream.fileno()))
            if signature(before) == seen == signature(path.lstat()) and path.resolve() == path:
                return data
        except FileNotFoundError:
            continue
    raise VaultError("Path changed during the read")


def scan_markdown(root, gaps):
    pending = [root]
    while pending:
        path = pending.pop()
        relative = path.relative_to(root).as_posix()
        try:
            before = path.lstat()
            if not stat.S_ISDIR(before.st_mode) or path.resolve() != path:
                raise VaultError("Directory changed during the scan")
            with os.scandir(path) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
            if signature(before) != signature(path.lstat()) or path.resolve() != path:
                raise VaultError("Directory changed during the scan")
        except (OSError, VaultError, RuntimeError) as exc:
            gaps[relative] = ("scan", str(exc))
            continue
        for entry in children:
            name = Path(entry.path).relative_to(root).as_posix()
            if excluded(name):
                continue
            try:
                name.encode("utf-8")
            except UnicodeEncodeError:
                gaps[relative] = ("scan", "A directory entry has a non-UTF-8 name")
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif name.lower().endswith(".md") and entry.is_file(follow_symlinks=False):
                    yield name
            except OSError as exc:
                gaps[name] = ("scan", str(exc))


def covered_by_gap(path, gaps):
    return any(gaps.get(str(parent), (None,))[0] == "scan"
               for parent in (PurePosixPath(path), *PurePosixPath(path).parents))


def confirmed_removed(root, path, gaps):
    if excluded(path):
        return True
    if covered_by_gap(path, gaps):
        return False
    target = root / path
    try:
        if not stat.S_ISREG(target.lstat().st_mode) or target.resolve() != target:
            return True
        # A case-insensitive filesystem can resolve a retired spelling to the new
        # note. Check the directory entries, including a renamed ancestor.
        parent = root
        for part in PurePosixPath(path).parts:
            with os.scandir(parent) as entries:
                if not any(entry.name == part for entry in entries):
                    return True
            parent = parent / part
        return False
    except (FileNotFoundError, NotADirectoryError):
        return True
    except (OSError, RuntimeError) as exc:
        gaps[path] = ("scan", str(exc))
        return False


def value_as_text(value):
    return value if isinstance(value, str) and value.strip() else None


def date_value(value):
    value = value_as_text(value)
    if value:
        try:
            if dt.date.fromisoformat(value).isoformat() == value:
                return value
        except ValueError:
            pass
    return None


def note_data(data, path):
    # A UTF-8 error affects the entire text. Invalid YAML still leaves searchable text.
    source = text(data, path)
    problem = None
    try:
        meta, body = metadata(data, path)
        meta = canonical(meta)
        tags = meta.get("tags", [])
        tags = [tags] if isinstance(tags, str) else tags
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise VaultError("Tags must be strings")
        raw = json.dumps(meta, ensure_ascii=False, allow_nan=False, sort_keys=True)
        raw.encode("utf-8")
    except (VaultError, TypeError, ValueError, RecursionError) as exc:
        last = str(exc).splitlines()
        problem = last[0] if last else type(exc).__name__
        meta, body, raw = {}, source, None
    relative = PurePosixPath(path)
    subject = relative.parts[0] if len(relative.parts) > 1 else None
    heading = re.search(r"^#[ \t]+(.+)$", body, re.M)
    title = value_as_text(meta.get("title")) or (heading[1].strip() if heading else relative.stem)
    ticket = meta.get("ticket_id")
    if type(ticket) is int:
        ticket = str(ticket)
    fields = (subject, title, value_as_text(meta.get("description")),
              date_value(meta.get("date_created")), date_value(meta.get("date_updated")),
              value_as_text(ticket), raw)
    return fields, body, meta, problem


def write_note(db, path, note_id, digest, fields, body, meta):
    if note_id is None:
        note_id = db.execute(
            "INSERT INTO notes VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (path, *fields, digest),
        ).lastrowid
    else:
        db.execute(
            """UPDATE notes SET subject = ?, title = ?, description = ?, date_created = ?,
                date_updated = ?, ticket_id = ?, metadata_json = ?, content_hash = ? WHERE id = ?""",
            (*fields, digest, note_id),
        )
        db.execute("DELETE FROM properties WHERE path = ?", (path,))
    db.execute(
        "INSERT OR REPLACE INTO note_text(rowid, path, title, description, body) VALUES (?, ?, ?, ?, ?)",
        (note_id, path, fields[1], fields[2], body),
    )
    for name, value in meta.items():
        items = value if isinstance(value, list) else [value]
        db.executemany("INSERT INTO properties VALUES (?, ?, ?, ?)", (
            (path, name, pos, json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            for pos, item in enumerate(items)
        ))


def remove_note(db, path, note_id):
    db.execute("DELETE FROM properties WHERE path = ?", (path,))
    db.execute("DELETE FROM note_text WHERE rowid = ?", (note_id,))
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def rebuild_schema(db, supported):
    # Disable foreign keys before entering the migration transaction. An older schema
    # may have an arbitrary table order. Dropping virtual tables removes their shadows.
    objects = db.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('view', 'trigger', 'table') AND substr(name, 1, 7) != 'sqlite_'"
    ).fetchall()
    objects.sort(key=lambda item: (
        {"trigger": 0, "view": 1, "table": 2}[item[0]],
        not item[2].lstrip().upper().startswith("CREATE VIRTUAL TABLE"),
    ))
    for kind, name, _ in objects:
        quoted = name.replace('"', '""')
        db.execute(f'DROP {kind} IF EXISTS "{quoted}"')
    for statement in SCHEMA:
        db.execute(statement)
    db.execute(f"PRAGMA user_version = {supported}")


def refresh(db, root, rebuild, had_snapshot):
    root_stat = root.stat()
    old = {path: (note_id, digest, metadata_missing)
           for path, note_id, digest, metadata_missing in
           db.execute("SELECT path, id, content_hash, metadata_json IS NULL FROM notes")}
    previous_gaps = {path: (kind, detail) for path, kind, detail in db.execute("SELECT * FROM coverage")}
    gaps = {}
    remaining = set(old)
    counts = dict.fromkeys(("added", "updated", "removed"), 0)

    for path in scan_markdown(root, gaps):
        remaining.discard(path)
        note_id, old_digest, metadata_missing = old.get(path, (None, None, False))
        try:
            data = read_saved(root / path)
            if (PurePosixPath(path).name == "index.md"
                    and data.startswith((INDEX_MARKER + b"\n", INDEX_MARKER + b"\r\n"))):
                if note_id is not None:
                    remove_note(db, path, note_id)
                    counts["removed"] += 1
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest == old_digest:
                if previous_gaps.get(path, (None,))[0] == "metadata":
                    gaps[path] = previous_gaps[path]
                    continue
                if not metadata_missing:
                    continue
                # An intervening scan gap may have replaced the metadata error.
            fields, body, meta, problem = note_data(data, path)
        except (OSError, VaultError, RuntimeError) as exc:
            gaps[path] = ("scan", str(exc))
            continue
        if problem:
            gaps[path] = ("metadata", problem)
        if digest == old_digest:
            continue
        write_note(db, path, note_id, digest, fields, body, meta)
        counts["updated" if note_id is not None else "added"] += 1

    for path in sorted(remaining):
        if not confirmed_removed(root, path, gaps):
            if not covered_by_gap(path, gaps):
                gaps[path] = ("scan", "Path appeared after its directory was scanned")
            continue
        remove_note(db, path, old[path][0])
        counts["removed"] += 1

    if "." in gaps or not os.path.samestat(root_stat, root.lstat()) or root.resolve() != root:
        raise VaultError("The vault root changed during the scan. Retry when the vault is available")
    if rebuild and had_snapshot and any(kind == "scan" for kind, _ in gaps.values()):
        raise VaultError("Cannot rebuild the older catalog while paths are inaccessible: " +
                         ", ".join(path for path, (kind, _) in sorted(gaps.items()) if kind == "scan"))

    for path in previous_gaps.keys() - gaps.keys():
        db.execute("DELETE FROM coverage WHERE path = ?", (path,))
    for path, issue in gaps.items():
        if issue != previous_gaps.get(path):
            db.execute("INSERT OR REPLACE INTO coverage VALUES (?, ?, ?)", (path, *issue))

    return {**counts, "coverage": [
        {"path": path, "kind": kind, "detail": detail}
        for path, (kind, detail) in sorted(gaps.items())
    ]}


def reader_path(root):
    try:
        reader = Path((root / ".venv/vault-sqlite3").read_text(encoding="utf-8").rstrip("\r\n"))
        if reader.is_absolute() and reader.is_file() and os.access(reader, os.X_OK):
            return str(reader)
    except (OSError, ValueError):
        pass
    return shutil.which("sqlite3")


def sync(root):
    database = None
    try:
        database = database_path(root)
        supported = schema_version()
        database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with closing(sqlite3.connect(database, timeout=5)) as db:
            # SQLite may need writable access to recover an interrupted writer
            # before even the first read. Check again after acquiring the lock.
            check_version(version(db), supported)
            db.execute("PRAGMA foreign_keys = OFF")
            with db:
                db.execute("BEGIN IMMEDIATE")
                # Another process may have rebuilt the database while we waited.
                found = version(db)
                check_version(found, supported)
                rebuild = found < supported
                had_snapshot = found > 0 or db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' LIMIT 1"
                ).fetchone() is not None
                if rebuild:
                    rebuild_schema(db, supported)
                result = refresh(db, root, rebuild, had_snapshot)
        return {"database": str(database), "sqlite3": reader_path(root), "schema": supported, **result}
    except (VaultError, OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        status = snapshot_status(database) if database else "No catalog path was resolved."
        raise VaultError(f"Catalog sync failed: {exc}. {status}") from exc
