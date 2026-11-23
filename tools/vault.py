#!/usr/bin/env python3
"""Optional local discovery and commit automation for Markdown vaults."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tempfile
import subprocess
import sys

# Discovery can run against a read-only vault. Keep Python's cache out of it too.
sys.dont_write_bytecode = True
from vault_notes import (
    FRONTMATTER, VaultError, canonical, excluded, metadata, text, yaml,
)

HOOK_MARKER = "# vault-framework: local pre-commit hook"


def git(root, *args, data=None, check=True, env=None):
    result = subprocess.run(["git", *args], cwd=root, input=data, capture_output=True, env=env)
    if check and result.returncode:
        raise VaultError(result.stderr.decode(errors="replace").strip() or "Git command failed")
    return result


def index_entries(root):
    entries = {}
    for record in git(root, "ls-files", "--stage", "-z").stdout.split(b"\0"):
        if not record:
            continue
        header, path_bytes = record.split(b"\t", 1)
        mode, oid, stage = header.decode().split()
        path = os.fsdecode(path_bytes)
        if stage != "0":
            raise VaultError("Resolve unmerged paths before updating staged timestamps")
        entries[path] = (mode, oid)
    return entries


def staged_snapshot(root):
    changed = git(root, "diff", "--cached", "--name-only", "-z").stdout.split(b"\0")
    changed_notes = {os.fsdecode(path) for path in changed if path.lower().endswith(b".md")}
    entries = index_entries(root)
    entries = {path: entry for path, entry in entries.items()
               if entry[0] in {"100644", "100755"} and path in changed_notes}
    request = "".join(oid + "\n" for _, oid in entries.values()).encode()
    stream = io.BytesIO(git(root, "cat-file", "--batch", data=request).stdout)
    files = {}
    for path in entries:
        _, kind, size = stream.readline().split()
        if kind != b"blob":
            raise VaultError(f"{path}: expected a Git blob")
        files[path] = stream.read(int(size))
        stream.read(1)
    return files, entries


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


def reconcile_commit(root):
    pending = git_path(root, "vault-partial-commit.json")
    if not pending.exists():
        return 0
    plan = json.loads(pending.read_bytes())
    if git(root, "rev-parse", "HEAD^{tree}").stdout.decode().strip() == plan["tree"]:
        actual = index_entries(root)
        # Preserve separately staged content.
        changes = {p: after for p, (before, after) in plan["entries"].items()
                   if actual.get(p) == (tuple(before) if before else None)}
        update_entries(root, changes)
    pending.unlink()
    return 0


def sync_catalog(root):
    try:
        import catalog
    except ImportError as exc:
        raise VaultError("Catalog sync needs a Python build with sqlite3. No snapshot could be checked.") from exc
    return catalog.sync(root)


def run_post_commit(root):
    reconcile_commit(root)
    try:
        result = sync_catalog(root)
        for issue in result["coverage"]:
            print(f'vault: Catalog coverage for {issue["path"]}: {issue["detail"]}', file=sys.stderr)
    except VaultError as exc:
        print(f"vault: {exc}", file=sys.stderr)
    return 0


def timestamp_notes(files):
    for path, data in sorted(files.items()):
        if not path.lower().endswith(".md") or excluded(path):
            continue
        try:
            meta, _ = metadata(data, path)
        except (VaultError, RecursionError):
            continue  # An unfinished draft can be committed.
        yield path, meta


def run_pre_commit(root):
    pending = git_path(root, "vault-partial-commit.json")
    pending.unlink(missing_ok=True)  # Discard any handoff from an aborted commit.
    files, entries = staged_snapshot(root)
    updates = {}
    working_updates = {}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    for path, meta in timestamp_notes(files):
        if "date_updated" not in meta:
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
    changes = {}
    for path, data in updates.items():
        oid = git(root, "hash-object", "-w", "--stdin", data=data).stdout.strip().decode()
        changes[path] = (entries[path][0], oid)
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
    commands.add_parser("sync", help="Refresh the local SQLite catalog from saved Markdown")
    commands.add_parser("pre-commit", help="Maintain staged timestamps and preserve partial staging")
    commands.add_parser("post-commit", help="Reconcile explicit-path commits, then refresh the catalog")
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
        print(json.dumps(sync_catalog(root), indent=2))
        return 0
    except (VaultError, OSError) as exc:
        print(f"vault: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
