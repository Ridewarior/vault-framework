# Vault maintenance tool

`vault.py` builds directory indexes and can maintain them during Git commits. Index generation works with ordinary local files and does not require Git.

The maintenance tool lives in `tools/` in the framework repository. The commands below use its installed location, `vault-tools/`, from a vault root.

## Manual setup

Install Python 3.10+ with virtual-environment support. In a vault containing the copied tool and requirements:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r vault-tools/requirements.txt
```

Keep the environment local to the device. On Windows, its interpreter is usually `.venv\Scripts\python.exe`. The tool uses PyYAML 6.x.

## Generate indexes

```sh
.venv/bin/python vault-tools/vault.py index
.venv/bin/python vault-tools/vault.py index --check
```

`index` reads the files and writes changed indexes. When a directory is no longer selected, the tool reports its old generated index so you can review and remove it. It leaves the file in place. The Git hook also reports retired indexes in staged content.

`--check` reports missing, stale, or retired indexes without writing and exits with code 1 if it finds any. Invalid input exits with code 2. Use `--vault /path/to/vault` before the command when running elsewhere.

The generator creates an `index.md` in each selected top-level directory. It groups entries by subdirectory and always shows the note title and relative path. It takes the title from `title`, the first H1, or the filename.

## Configuration

Edit `vault.config.json`, then regenerate. The starter defaults are:

```json
{
  "indexes": {
    "roots": ["*"],
    "exclude_paths": ["inbox", "vault-framework", "guidelines", "templates", "attachments", "vault-tools"],
    "properties": ["description"],
    "display_tags": null,
    "include_tags": [],
    "exclude_tags": ["thought-bubbles"],
    "include_properties": {},
    "exclude_properties": {}
  },
  "timestamps": {"enabled": true}
}
```

| Setting | Meaning |
| --- | --- |
| `roots` | `["*"]` selects top-level directories; a list selects named roots; `[]` selects none |
| `exclude_paths` | Exclude a vault-relative path and its descendants |
| `properties` | Extra columns, in order |
| `display_tags` | If `tags` is a column, `null` shows all tags, a list selects tags, and `[]` hides them |
| `include_tags` | Match any listed tag; an empty list adds no restriction |
| `exclude_tags` | Exclude matching notes |
| `include_properties` | Require all listed property/value pairs to match |
| `exclude_properties` | Exclude a note when any listed pair matches |
| `timestamps.enabled` | Enable or disable date updates in the Git hook |

Tag filters include children, so `research` matches `research/backups`. Property filters use exact values; dates compare as ISO strings. Missing fields do not match. Exclusions win over inclusions.

The framework copy and all `guidelines/` directories are excluded, including scoped guidelines. They are supporting files and do not need note metadata. Other default exclusions can be edited.

Included notes need valid YAML, nonempty lowercase tags, and a description. Hidden paths, symlinks, and files named `index.md` are skipped. The tool refuses to overwrite an authored index without its generated marker. It leaves unchanged output alone.

## Optional Git hook

For a vault using Git, install the hook once per checkout:

```sh
.venv/bin/python vault-tools/vault.py install-hook
```

The installer sets up both `pre-commit` and `post-commit` with the environment's interpreter path. Rerun it after moving the environment or upgrading a checkout that has only the older pre-commit hook. If you manage hooks yourself, call the matching `vault.py pre-commit` and `vault.py post-commit` commands from your hooks.

On a commit, the hook reads staged notes and staged configuration. It updates the generated indexes and existing `date_updated` fields on included changed notes. Dates use UTC. It preserves `date_created`, and a date-only edit does not cause another automatic update.

Unstaged prose and untracked notes stay out of the commit. If a generated index has content that would be overwritten, the hook stops for you to resolve it. A working note with unfinished YAML or a separately changed timestamp is left untouched; Git may then show the timestamp difference.

Timestamps currently use the same selection filters as indexes. The hook does not coordinate concurrent editor writes. Git clients can skip hooks, so behavior needs checking in each client.

If the pre-commit hook cannot write a working file or update Git's index, it rolls back the working files it touched. For a commit with explicit paths, Git uses a temporary index. The post-commit hook carries the generated entries into the regular index after the commit and preserves independently staged edits.

Use a direct YAML scalar for `date_updated`. Quoted keys, quoted dates, and block scalars are supported. An anchored, aliased, or inherited timestamp needs an explicit date before the hook can update it.

## Verification

Native Git on Linux is tested, including initial commits, partial staging, explicit-path commits, and alternate indexes. Other systems and Git clients remain unverified.

In this repository, run `python3 -m unittest discover -s tests -v`. Tests use temporary directories and repositories, without downloading packages or installing a hook here.
