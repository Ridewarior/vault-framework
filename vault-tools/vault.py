#!/usr/bin/env python3
"""Optional local index and commit automation for Markdown vaults."""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
from urllib.parse import quote

try:
    import yaml
except ImportError:
    raise SystemExit("Install the optional dependency: python -m pip install -r vault-tools/requirements.txt")

MARKER = "<!-- vault-framework: generated index -->"
HOOK_MARKER = "# vault-framework: local pre-commit hook"
FRONTMATTER = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", re.M | re.S)
STAMP = re.compile(r"^date_updated[ \t]*:[^\r\n]*", re.M)
DEFAULT_INDEXES = {
    "roots": ["*"],
    "exclude_paths": ["inbox", "vault-framework", "guidelines", "templates", "attachments", "vault-tools"],
    "properties": ["description"],
    "display_tags": None,
    "include_tags": [],
    "exclude_tags": ["thought-bubbles"],
    "include_properties": {},
    "exclude_properties": {},
}


class VaultError(Exception):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise VaultError("Frontmatter keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def git(root, *args, data=None, check=True):
    result = subprocess.run(["git", *args], cwd=root, input=data, capture_output=True)
    if check and result.returncode:
        raise VaultError(result.stderr.decode(errors="replace").strip() or "Git command failed")
    return result


def text(data, path):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VaultError(f"{path}: expected UTF-8 text") from exc


def metadata(data, path):
    source = text(data, path)
    match = FRONTMATTER.match(source)
    if not match:
        if source.lstrip("\ufeff").splitlines()[:1] == ["---"]:
            raise VaultError(f"{path}: unclosed frontmatter")
        return {}, source
    try:
        value = yaml.load(match[1], Loader=UniqueLoader)
    except (yaml.YAMLError, VaultError, ValueError) as exc:
        raise VaultError(f"{path}: invalid frontmatter: {exc}") from exc
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise VaultError(f"{path}: frontmatter must be a mapping")
    return value, source[match.end():]


def relative_path(value):
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and "\\" not in value


def configuration(data):
    try:
        config = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise VaultError(f"Invalid vault.config.json: {exc}") from exc
    if not isinstance(config, dict) or set(config) - {"indexes", "timestamps"}:
        raise VaultError("Configuration accepts only indexes and timestamps sections")
    indexes = config.get("indexes", {})
    timestamps = config.get("timestamps", {})
    if not isinstance(indexes, dict) or set(indexes) - DEFAULT_INDEXES.keys():
        raise VaultError("Unknown index configuration field")
    if not isinstance(timestamps, dict) or set(timestamps) - {"enabled"}:
        raise VaultError("Timestamps accepts only enabled")
    indexes = {**DEFAULT_INDEXES, **indexes}
    for field in ("roots", "exclude_paths", "properties", "include_tags", "exclude_tags"):
        values = indexes[field]
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
            raise VaultError(f"indexes.{field} must be a list of nonempty strings")
        if len(set(values)) != len(values):
            raise VaultError(f"indexes.{field} contains duplicate values")
    for value in indexes["roots"]:
        if value != "*" and (not relative_path(value) or len(PurePosixPath(value).parts) != 1 or value.startswith(".")):
            raise VaultError("Index roots must be top-level directory names")
    if "*" in indexes["roots"] and indexes["roots"] != ["*"]:
        raise VaultError("Use roots [\"*\"] or a list of explicit roots")
    if not all(relative_path(p) and p != "." for p in indexes["exclude_paths"]):
        raise VaultError("Excluded paths must be vault-relative paths")
    if indexes["display_tags"] is not None and (
        not isinstance(indexes["display_tags"], list)
        or not all(isinstance(v, str) for v in indexes["display_tags"])
    ):
        raise VaultError("display_tags must be null or a list of tags")
    for field in ("include_properties", "exclude_properties"):
        if not isinstance(indexes[field], dict):
            raise VaultError(f"indexes.{field} must be an object")
    enabled = timestamps.get("enabled", True)
    if not isinstance(enabled, bool):
        raise VaultError("timestamps.enabled must be a boolean")
    return indexes, enabled


def excluded(path, config):
    parts = PurePosixPath(path).parts
    return (
        path == "vault-framework" or path.startswith("vault-framework/")
        or "guidelines" in parts
        or any(part.startswith(".") for part in parts)
        or any(
            path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
            for prefix in config["exclude_paths"]
        )
    )


def tag_matches(tag, parent):
    return tag == parent or tag.startswith(parent + "/")


def canonical(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    return value


def selected(meta, config):
    tags = meta.get("tags", [])
    tags = [tags] if isinstance(tags, str) else tags
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise VaultError("tags must be a list of strings")
    def tagged(patterns):
        return any(tag_matches(tag, parent) for tag in tags for parent in patterns)
    if tagged(config["exclude_tags"]):
        return False
    if config["include_tags"] and not tagged(config["include_tags"]):
        return False
    if not all(key in meta and canonical(meta[key]) == expected for key, expected in config["include_properties"].items()):
        return False
    if any(key in meta and canonical(meta[key]) == expected for key, expected in config["exclude_properties"].items()):
        return False
    return True


def roots_for(directories, config):
    roots = sorted(d for d in directories if not excluded(d, config))
    if config["roots"] != ["*"]:
        missing = set(config["roots"]) - directories
        if missing:
            raise VaultError(f"Configured roots do not exist: {', '.join(sorted(missing))}")
        roots = [d for d in roots if d in config["roots"]]
    return roots


def notes_for(files, roots, config):
    notes = {}
    for path, data in sorted(files.items()):
        parts = PurePosixPath(path).parts
        if len(parts) < 2 or parts[0] not in roots or excluded(path, config) or parts[-1] == "index.md":
            continue
        meta, body = metadata(data, path)
        try:
            if not selected(meta, config):
                continue
        except VaultError as exc:
            raise VaultError(f"{path}: {exc}") from exc
        tags = meta.get("tags")
        if not isinstance(tags, list) or not tags or not all(isinstance(t, str) and t and t == t.lower() for t in tags):
            raise VaultError(f"{path}: structured notes require nonempty lowercase tags")
        if not isinstance(meta.get("description"), str) or not meta["description"].strip():
            raise VaultError(f"{path}: structured notes require a description")
        heading = re.search(r"^#\s+(.+)$", body, re.M)
        title = meta.get("title") or (heading[1].strip() if heading else PurePosixPath(path).stem)
        notes[path] = (meta, str(title))
    return notes


def cell(value):
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(canonical(v)) for v in value)
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False, default=str)
    else:
        value = str(canonical(value))
    return " ".join(value.split()).replace("&", "&amp;").replace("<", "&lt;").replace("\\", "\\\\").replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def index_content(root, notes, config):
    lines = [MARKER, "", f"# {cell(root)} index", "", "Generated from note metadata and vault.config.json. Edit the sources, then regenerate.", ""]
    groups = {}
    for path, (meta, title) in notes.items():
        relative = PurePosixPath(path).relative_to(root)
        if PurePosixPath(path).parts[0] == root:
            groups.setdefault(str(relative.parent), []).append((str(relative), meta, title))
    for directory, entries in sorted(groups.items()):
        lines.extend([f"## {cell(directory)}", ""])
        labels = ["Note", "Path", *[cell(p) for p in config["properties"]]]
        lines.extend(["| " + " | ".join(labels) + " |", "| " + " | ".join("---" for _ in labels) + " |"])
        for path, meta, title in sorted(entries, key=lambda entry: (entry[0].casefold(), entry[0])):
            values = []
            for prop in config["properties"]:
                value = meta.get(prop)
                if prop == "tags" and config["display_tags"] is not None:
                    value = [t for t in value or [] if any(tag_matches(t, p) for p in config["display_tags"])]
                values.append(cell(value))
            target = quote(path, safe="/")
            lines.append("| " + " | ".join([f"[{cell(title)}]({target})", cell(path), *values]) + " |")
        lines.append("")
    if not groups:
        lines.extend(["No matching structured notes.", ""])
    return ("\n".join(lines)).encode("utf-8")


def render_indexes(files, roots, config):
    notes = notes_for(files, roots, config)
    updates = {}
    for root in roots:
        output = root + "/index.md"
        if output in files and not text(files[output], output).startswith(MARKER + "\n"):
            raise VaultError(f"{output}: refusing to replace an authored index")
        result = index_content(root, {p: n for p, n in notes.items() if p.startswith(root + "/")}, config)
        if files.get(output) != result:
            updates[output] = result
    return updates


def filesystem_snapshot(root):
    files = {}
    directories = set()
    for item in root.iterdir():
        if item.is_dir() and not item.is_symlink() and not item.name.startswith("."):
            directories.add(item.name)
    for parent, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and not (Path(parent) / d).is_symlink()]
        for name in names:
            path = Path(parent) / name
            if name.endswith(".md") and not path.is_symlink():
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files, directories


def staged_snapshot(root):
    entries = {}
    directories = set()
    for record in git(root, "ls-files", "--stage", "-z").stdout.split(b"\0"):
        if not record:
            continue
        header, path_bytes = record.split(b"\t", 1)
        mode, oid, stage = header.decode().split()
        path = os.fsdecode(path_bytes)
        if stage != "0":
            raise VaultError("Resolve unmerged paths before generating indexes")
        if "/" in path:
            directories.add(path.split("/", 1)[0])
        if mode in {"100644", "100755"} and (path.endswith(".md") or path == "vault.config.json"):
            entries[path] = (mode, oid)
    request = "".join(oid + "\n" for _, oid in entries.values()).encode()
    stream = io.BytesIO(git(root, "cat-file", "--batch", data=request).stdout)
    files = {}
    for path in entries:
        _, kind, size = stream.readline().split()
        if kind != b"blob":
            raise VaultError(f"{path}: expected a Git blob")
        files[path] = stream.read(int(size))
        stream.read(1)
    return files, directories, entries


def safe_path(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise VaultError(f"{relative}: refusing a symlinked output path")
    return path


def timestamp_edit(data, path, value=None):
    source = text(data, path)
    frontmatter = FRONTMATTER.match(source)
    if not frontmatter:
        return data
    field = STAMP.search(frontmatter[1])
    if not field:
        return data
    start, end = frontmatter.start(1) + field.start(), frontmatter.start(1) + field.end()
    replacement = ""
    if value is not None:
        comment = re.search(r"[ \t]+#.*$", field[0])
        replacement = "date_updated: " + value + (comment[0] if comment else "")
    return (source[:start] + replacement + source[end:]).encode("utf-8")


def run_index(root, check):
    config, _ = configuration((root / "vault.config.json").read_bytes())
    files, directories = filesystem_snapshot(root)
    updates = render_indexes(files, roots_for(directories, config), config)
    paths = {name: safe_path(root, name) for name in updates}
    if check:
        for name in updates:
            print(f"Stale or missing: {name}")
        return 1 if updates else 0
    for name, data in updates.items():
        paths[name].write_bytes(data)
        print(f"Updated {name}")
    if not updates:
        print("Indexes are current.")
    return 0


def run_pre_commit(root):
    files, directories, entries = staged_snapshot(root)
    if "vault.config.json" not in files:
        raise VaultError("Stage vault.config.json before using the hook")
    config, timestamps = configuration(files["vault.config.json"])
    roots = roots_for(directories, config)
    updates = {}
    working_updates = {}
    if timestamps:
        changed = {os.fsdecode(p) for p in git(root, "diff", "--cached", "--name-only", "-z").stdout.split(b"\0") if p}
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        for path, (meta, _) in notes_for(files, roots, config).items():
            if path not in changed or "date_updated" not in meta:
                continue
            date = canonical(meta["date_updated"])
            if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                raise VaultError(f"{path}: date_updated must be an ISO date")
            try:
                dt.date.fromisoformat(date)
            except ValueError as exc:
                raise VaultError(f"{path}: invalid date_updated") from exc
            previous = git(root, "show", "HEAD:" + path, check=False)
            if previous.returncode == 0 and timestamp_edit(previous.stdout, path) == timestamp_edit(files[path], path):
                continue
            updated = timestamp_edit(files[path], path, today)
            if updated == files[path]:
                continue
            updates[path] = updated
            working_path = safe_path(root, path)
            if working_path.exists():
                current = working_path.read_bytes()
                # Change only the generated field, retaining unstaged prose and other metadata.
                try:
                    working_meta, _ = metadata(current, path)
                    if canonical(working_meta.get("date_updated")) == date:
                        working_updates[path] = timestamp_edit(current, path, today)
                except VaultError:
                    pass  # An unfinished working copy is left untouched.
    candidate = {**files, **updates}
    indexes = render_indexes(candidate, roots, config)
    for path, data in indexes.items():
        target = safe_path(root, path)
        current = target.read_bytes() if target.exists() else None
        if current != files.get(path) and current != data:
            raise VaultError(f"{path}: has unstaged or untracked content; preserve or stage it before retrying")
        working_updates[path] = data
    updates.update(indexes)
    # All ownership and working-copy checks finish before mutating the candidate index.
    index_records = []
    for path, data in updates.items():
        oid = git(root, "hash-object", "-w", "--stdin", data=data).stdout.strip().decode()
        mode = entries.get(path, ("100644", ""))[0]
        index_records.append(f"{mode} {oid}\t".encode() + os.fsencode(path) + b"\0")
    if index_records:
        git(root, "update-index", "-z", "--index-info", data=b"".join(index_records))
    for path, data in working_updates.items():
        safe_path(root, path).write_bytes(data)
    if updates:
        print(f"Vault hook updated {len(updates)} staged file(s).")
    return 0


def install_hook(root):
    actual = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel").stdout.strip())).resolve()
    if actual != root.resolve():
        raise VaultError("Install the hook from the vault Git root")
    custom = git(root, "config", "--get", "core.hooksPath", check=False)
    if custom.returncode == 0:
        raise VaultError("core.hooksPath is already configured; integrate vault-tools/vault.py pre-commit with that hook manually")
    hook = Path(os.fsdecode(git(root, "rev-parse", "--git-path", "hooks/pre-commit").stdout.strip()))
    if not hook.is_absolute():
        hook = root / hook
    if hook.is_symlink() or (hook.exists() and HOOK_MARKER not in hook.read_text()):
        raise VaultError("An existing pre-commit hook is present; integrate it manually")
    if not (root / "vault-tools/vault.py").is_file():
        raise VaultError("Expected the copied tool at vault-tools/vault.py")
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_bytes(("#!/bin/sh\n" + HOOK_MARKER + "\nexec " + shlex.quote(sys.executable) + ' "$(git rev-parse --show-toplevel)/vault-tools/vault.py" pre-commit\n').encode("utf-8"))
    hook.chmod(0o755)
    print(f"Installed {hook}. Reinstall if this Python environment moves.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path.cwd(), help="Vault root, default: current directory")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Generate configured recursive directory indexes")
    index.add_argument("--check", action="store_true", help="Report stale output without writing")
    commands.add_parser("pre-commit", help="Generate from the staged snapshot and preserve partial staging")
    commands.add_parser("install-hook", help="Install an optional local pre-commit hook")
    args = parser.parse_args()
    root = args.vault.resolve()
    try:
        if args.command == "install-hook":
            return install_hook(root)
        if args.command == "pre-commit":
            return run_pre_commit(root)
        return run_index(root, args.check)
    except (VaultError, OSError) as exc:
        print(f"vault: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
