# Vault maintenance tool

`vault.py sync` builds and refreshes a local SQLite catalog of Markdown notes. The optional Git hooks maintain staged dates and refresh the catalog after a commit. Catalog sync works with any local storage.

The maintenance tool lives in `tools/` in the framework repository. The commands below use its installed location, `vault-tools/`, from a vault root.

## Manual setup

Install Python 3.10+ with virtual-environment support. In a vault containing the copied tool and requirements:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r vault-tools/requirements.txt
```

Keep the environment local to the device. On Windows, its interpreter is usually `.venv\Scripts\python.exe`. The tool uses PyYAML 6.x. For discovery, use a Python build with SQLite FTS5 and a `sqlite3` command with FTS5 and JSON support. The setup command can prepare and check both.

## Sync and query

```sh
.venv/bin/python vault-tools/vault.py sync
```

Run the command from the vault root or pass `--vault /path/to/vault` before `sync`. The JSON output gives the database path, the sqlite3 executable path (or null if unavailable), the schema version, counts of added, updated, and removed notes, and coverage gaps. The catalog lives in the per-user cache, under `vault-framework/catalogs/`. The cache base is `XDG_CACHE_HOME` or `~/.cache` on Linux, `~/Library/Caches` on macOS, and `LOCALAPPDATA` on Windows. Each canonical vault path has its own catalog on that device. You can delete the cache to clear it and sync to build it again.

Use `sqlite3 -readonly -json` with the reported database path. The [discovery skill](skills/discover-vault/SKILL.md) walks through finding notes and links to the schema and sample queries.

Sync compares saved file contents with the last catalog even if Git status is unchanged. A move adds the new path and removes the old one. It updates metadata, tags, full text, and coverage in one transaction. Unreadable paths may retain an earlier entry and appear as `scan` gaps. Invalid frontmatter leaves the note searchable by text and path, with a `metadata` gap and no tag or property data. A failed sync explains whether it could find a previous snapshot.

The framework release declares the catalog schema in `vault-framework/CATALOG_SCHEMA_VERSION`. SQLite stores it in `PRAGMA user_version`. Sync rebuilds an older schema from Markdown in a transaction and refuses a newer schema. Each note keeps its parsed frontmatter as JSON. An index on property names and values supports exact lookups, including members of vault-specific lists.

## Configuration

The starter uses:

```json
{
  "catalog": {},
  "timestamps": {"enabled": true}
}
```

The catalog includes saved Markdown in the vault root, subject folders, and inbox, including raw captures and thought bubbles. The included notes may omit frontmatter. It skips hidden paths, symlinks, the framework copy, and root and scoped `guidelines/`. Subject READMEs and authored `index.md` files are searchable.

To customize the scope, set `catalog.exclude_paths` to a list of vault-relative files or directories. A directory exclusion also applies to descendants. The list replaces the default `["AGENTS.md", "attachments", "templates", "vault-tools"]`. Set `timestamps.enabled` to `false` to turn off staged date maintenance without disabling catalog refreshes.

## Optional Git hooks

For a vault using Git, install the hooks once per checkout:

```sh
.venv/bin/python vault-tools/vault.py install-hook
```

Rerun the installer after moving the environment or upgrading a checkout that only has a pre-commit hook. If you manage hooks yourself, call `vault.py pre-commit` and `vault.py post-commit` from the matching hooks.

Stage `vault.config.json` before the first commit. Pre-commit reads staged notes and configuration. It updates an existing `date_updated` on changed notes using UTC. A date-only edit stays as entered. The hook preserves unstaged prose, and leaves an unfinished working copy or separately edited working date alone. If it cannot write a working file or update Git's index, it rolls back the working files it touched.

Use a direct YAML scalar for `date_updated`. Quoted keys, quoted dates, and block scalars are supported. Give an anchored, aliased, or inherited date its own value before the hook can update it.

Post-commit reconciles date updates from an explicit-path commit with the regular Git index. It then syncs from saved working files, including unstaged changes and untracked notes. Catalog failures appear after the commit and do not reject it. If a Git client skips hooks, run sync before searching.

## Verification

In the framework repository, run `python3 -m unittest discover -s tests -v` with PyYAML installed. The tests use temporary local catalogs and Git repositories. Git clients outside native Git and the package-manager installation paths need device testing.
