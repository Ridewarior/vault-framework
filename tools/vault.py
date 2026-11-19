#!/usr/bin/env python3
"""Optional local index and commit automation for Markdown vaults."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import datetime as dt
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import tempfile
import subprocess
import sys
from urllib.parse import quote

try:
    import yaml
except ImportError:
    requirements = Path(__file__).resolve().with_name("requirements.txt")
    raise SystemExit(f'Install the optional dependency: python -m pip install -r "{requirements}"')

MARKER = "<!-- vault-framework: generated index -->"
HOOK_MARKER = "# vault-framework: local pre-commit hook"
FRONTMATTER = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", re.M | re.S)
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


def git(root, *args, data=None, check=True, env=None):
    result = subprocess.run(["git", *args], cwd=root, input=data, capture_output=True, env=env)
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
    indexes["exclude_paths"] = [str(PurePosixPath(p)) for p in indexes["exclude_paths"]]
    if len(set(indexes["exclude_paths"])) != len(indexes["exclude_paths"]):
        raise VaultError("indexes.exclude_paths contains equivalent paths")
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


def exact_value(actual, expected):
    if isinstance(actual, bool) != isinstance(expected, bool):
        return False
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(exact_value(a, b) for a, b in zip(actual, expected))
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(exact_value(actual[k], expected[k]) for k in actual)
    return actual == expected


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
    if not all(key in meta and exact_value(canonical(meta[key]), expected) for key, expected in config["include_properties"].items()):
        return False
    if any(key in meta and exact_value(canonical(meta[key]), expected) for key, expected in config["exclude_properties"].items()):
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


def generated_index(data):
    return data.partition(b"\n")[0].removesuffix(b"\r") == MARKER.encode()


def render_indexes(files, roots, config):
    notes = notes_for(files, roots, config)
    updates = {}
    for root in roots:
        output = root + "/index.md"
        if output in files and not generated_index(files[output]):
            raise VaultError(f"{output}: refusing to replace an authored index")
        result = index_content(root, {p: n for p, n in notes.items() if p.startswith(root + "/")}, config)
        if files.get(output, b"").replace(b"\r\n", b"\n") != result:
            updates[output] = result
    return updates


def report_retired_indexes(files, roots):
    active = {root + "/index.md" for root in roots}
    retired = sorted(
        path for path, data in files.items()
        if path.count("/") == 1 and path.endswith("/index.md")
        and path not in active and generated_index(data)
    )
    for path in retired:
        print(f"Retired index: {path}. Review and remove it if no longer needed.", file=sys.stderr)
    return bool(retired)


def filesystem_snapshot(root, config):
    directories = {p.name for p in root.iterdir() if not p.name.startswith(".") and not p.is_symlink() and p.is_dir()}
    roots = roots_for(directories, config)
    files = {}
    for name in directories:
        folder = root / name
        if name in {"vault-framework", "guidelines"}:
            continue  # These directories cannot be selected, even with custom filters.
        if name not in roots:
            # A retired root can still contain a generated index.
            index = folder / "index.md"
            if not index.is_symlink() and index.is_file():
                with index.open("rb") as stream:
                    files[name + "/index.md"] = stream.readline(len(MARKER) + 2)
            continue
        for parent, dirs, names in os.walk(folder):
            directory = Path(parent)
            dirs[:] = [d for d in dirs if not (directory / d).is_symlink()
                       and not excluded((directory / d).relative_to(root).as_posix(), config)]
            for filename in names:
                path = directory / filename
                relative = path.relative_to(root).as_posix()
                if filename == "index.md" and directory != folder:
                    continue
                if not filename.endswith(".md") or path.is_symlink():
                    continue
                if filename == "index.md" or not excluded(relative, config):
                    files[relative] = path.read_bytes()
    return files, roots


def index_entries(root):
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
        entries[path] = (mode, oid)
    return entries, directories


def staged_snapshot(root):
    entries, directories = index_entries(root)
    entries = {path: entry for path, entry in entries.items()
               if entry[0] in {"100644", "100755"} and (path.endswith(".md") or path == "vault.config.json")}
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
    meta, _ = metadata(data, path)
    if "date_updated" not in meta:
        return data
    mapping = yaml.compose(frontmatter[1], Loader=yaml.SafeLoader)
    for key, node in mapping.value:
        if key.value != "date_updated":
            continue
        start = frontmatter.start(1) + node.start_mark.index
        end = frontmatter.start(1) + node.end_mark.index
        raw = source[start:end]
        if (not isinstance(node, yaml.ScalarNode) or node.start_mark.index < key.end_mark.index
                or raw.startswith(("&", "!", "*"))):
            break
        replacement = value or "0001-01-01"  # Mask dates when comparing two revisions.
        if node.style in ("'", '"'):
            replacement = node.style + replacement + node.style
        elif node.style in ("|", ">"):
            header, newline, body = raw.partition("\n")
            if not re.fullmatch(r"\s*\d{4}-\d{2}-\d{2}\s*", body):
                break
            replacement = header + newline + re.sub(r"\d{4}-\d{2}-\d{2}", replacement, body)
        return (source[:start] + replacement + source[end:]).encode("utf-8")
    raise VaultError(f"{path}: use a direct scalar date_updated value without anchors or aliases")


def run_index(root, check):
    config, _ = configuration((root / "vault.config.json").read_bytes())
    files, roots = filesystem_snapshot(root, config)
    updates = render_indexes(files, roots, config)
    paths = {name: safe_path(root, name) for name in updates}
    retired = report_retired_indexes(files, roots)
    if check:
        for name in updates:
            print(f"Stale or missing: {name}")
        return 1 if updates or retired else 0
    for name, data in updates.items():
        paths[name].write_bytes(data)
        print(f"Updated {name}")
    if not updates and not retired:
        print("Indexes are current.")
    return 0


@contextmanager
def replace_for_commit(target, data):
    """Publish one file and keep its original until Git accepts the batch."""
    exists = target.exists()
    if exists:
        with target.open("r+b"):  # Honor read-only files before replacing a directory entry.
            pass
    scratch = Path(tempfile.mkdtemp(prefix=".vault-hook-", dir=target.parent))
    backup = scratch / "original"
    incoming = scratch / "incoming"
    moved = installed = keep_backup = False
    try:
        incoming.write_bytes(data)
        if exists:
            shutil.copymode(target, incoming)
            os.replace(target, backup)
            moved = True
        os.replace(incoming, target)
        installed = True
        yield
    except BaseException:
        try:
            if moved:
                os.replace(backup, target)
            elif installed:
                target.unlink()
        except OSError as exc:
            keep_backup = True
            raise VaultError(f"Could not restore {target}; recovery files: {scratch}") from exc
        raise
    finally:
        if not keep_backup:
            shutil.rmtree(scratch, ignore_errors=True)


def git_path(root, name):
    return root / os.fsdecode(git(root, "rev-parse", "--git-path", name).stdout.rstrip(b"\n"))


def update_entries(root, entries, env=None):
    records = b"".join(
        f"{mode} {oid}\t".encode() + os.fsencode(path) + b"\0"
        for path, (mode, oid) in entries.items()
    )
    if records:
        git(root, "update-index", "-z", "--index-info", data=records, env=env)


def partial_commit_plan(root, entries, changes):
    # Native Git commits explicit paths through a disposable next-index-PID.lock.
    # Its post-commit hook runs after Git reinstates the user's index.
    active = root / os.environ.get("GIT_INDEX_FILE", "")
    if not (re.fullmatch(r"next-index-\d+\.lock", active.name)
            and active.resolve() == git_path(root, active.name).resolve()):
        return None
    if not os.access(git_path(root, "hooks/post-commit"), os.X_OK):
        raise VaultError("Reinstall the vault hooks before committing explicit paths")
    with tempfile.TemporaryDirectory(dir=active.parent) as temp:
        candidate = Path(temp) / "index"
        shutil.copy2(active, candidate)
        env = {**os.environ, "GIT_INDEX_FILE": str(candidate)}
        update_entries(root, changes, env)
        tree = git(root, "write-tree", env=env).stdout.decode().strip()
    return json.dumps({
        "tree": tree,
        "entries": {p: [entries.get(p), after] for p, after in changes.items()},
    }).encode()


def run_post_commit(root):
    pending = git_path(root, "vault-partial-commit.json")
    if not pending.exists():
        return 0
    plan = json.loads(pending.read_bytes())
    if git(root, "rev-parse", "HEAD^{tree}").stdout.decode().strip() == plan["tree"]:
        actual, _ = index_entries(root)
        # Preserve separately staged content, including edits to a generated index.
        changes = {p: after for p, (before, after) in plan["entries"].items()
                   if actual.get(p) == (tuple(before) if before else None)}
        update_entries(root, changes)
    pending.unlink()
    return 0


def run_pre_commit(root):
    pending = git_path(root, "vault-partial-commit.json")
    pending.unlink(missing_ok=True)  # Discard any handoff from an aborted commit.
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
            date_text = date.rstrip("\r\n") if isinstance(date, str) else date
            if not isinstance(date_text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
                raise VaultError(f"{path}: date_updated must be an ISO date")
            try:
                dt.date.fromisoformat(date_text)
            except ValueError as exc:
                raise VaultError(f"{path}: invalid date_updated") from exc
            previous = git(root, "show", "HEAD:" + path, check=False)
            if previous.returncode == 0:
                try:
                    old_content = timestamp_edit(previous.stdout, path)
                except VaultError:
                    old_content = None  # Permit a staged correction to malformed historical YAML.
                if old_content == timestamp_edit(files[path], path):
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
        if (current != files.get(path) and current != data
                and (current is None or current.replace(b"\r\n", b"\n") not in (files.get(path), data))):
            raise VaultError(f"{path}: has unstaged or untracked content; preserve or stage it before retrying")
        working_updates[path] = data
    updates.update(indexes)
    changes = {}
    for path, data in updates.items():
        oid = git(root, "hash-object", "-w", "--stdin", data=data).stdout.strip().decode()
        changes[path] = (entries.get(path, ("100644", ""))[0], oid)
    if changes:
        plan = partial_commit_plan(root, entries, changes)
        with ExitStack() as transaction:
            for path, data in working_updates.items():
                transaction.enter_context(replace_for_commit(safe_path(root, path), data))
            if plan is not None:
                transaction.enter_context(replace_for_commit(pending, plan))
            # Git atomically locks and replaces the active index. It is the last write.
            update_entries(root, changes)
    if updates:
        print(f"Vault hook updated {len(updates)} staged file(s).")
    report_retired_indexes(files, roots)
    return 0


def install_hook(root):
    actual = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel").stdout.strip())).resolve()
    if actual != root.resolve():
        raise VaultError("Install the hook from the vault Git root")
    custom = git(root, "config", "--get", "core.hooksPath", check=False)
    if custom.returncode == 0:
        raise VaultError("core.hooksPath is already configured; integrate both vault pre-commit and post-commit commands manually")
    hooks = [git_path(root, "hooks/" + name) for name in ("pre-commit", "post-commit")]
    for hook in hooks:
        if hook.is_symlink() or (hook.exists() and HOOK_MARKER not in hook.read_text()):
            raise VaultError(f"An existing hook is present at {hook}; integrate the vault hooks manually")
    if not (root / "vault-tools/vault.py").is_file():
        raise VaultError("Expected the copied tool at vault-tools/vault.py")
    for hook in hooks:
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_bytes(("#!/bin/sh\n" + HOOK_MARKER + "\nexec " + shlex.quote(sys.executable)
                          + ' "$(git rev-parse --show-toplevel)/vault-tools/vault.py" ' + hook.name + "\n").encode())
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
    commands.add_parser("post-commit", help="Reconcile generated entries after an explicit-path commit")
    commands.add_parser("install-hook", help="Install the local pre-commit and post-commit hooks")
    args = parser.parse_args()
    root = args.vault.resolve()
    try:
        if args.command == "install-hook":
            return install_hook(root)
        if args.command == "pre-commit":
            return run_pre_commit(root)
        if args.command == "post-commit":
            return run_post_commit(root)
        return run_index(root, args.check)
    except (VaultError, OSError) as exc:
        print(f"vault: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
