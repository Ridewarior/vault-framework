# Working on the vault framework

This repository contains the shared rules, starter files, and installer for Markdown vaults. The goal is for a user or agent to find the reasoning behind a decision and resume unfinished work from the notes. Keep the notes readable in any editor and usable without the optional search tools.

Put conventions that apply to every vault in `framework/`. Put editable defaults in `starter/`. A workflow that belongs to one kind of vault, such as tracking tickets, belongs in `examples/`.

## Where to work

| Task | Read |
| --- | --- |
| Change shared rules | [Framework](framework/README.md) |
| Change structure or metadata | [Organization](framework/organization.md) and [notes and upkeep](framework/notes.md) |
| Change starter governance or notes | [Starter guidelines](starter/guidelines/README.md) and [templates](starter/templates) |
| Change work-vault rules | [Work example](examples/work/README.md) and its [local guidelines](examples/work/guidelines/README.md) |
| Change agent guidance | [Sample instructions](starter/AGENTS.md) and the framework's [shared principles](framework/README.md) |
| Change catalog or hook behavior | [Tool guide](tools/README.md) and [tests](tests/test_vault.py) |
| Change setup or updates | [Setup guide](docs/setup.md), [manual setup](docs/manual-setup.md), and [Go tests](installer/setup_test.go) |

## Boundaries

- This repo's `framework/` and `tools/` install as `vault-framework/` and `vault-tools/`. Local rules live in `guidelines/` and `AGENTS.md`.
- Core files are editor-agnostic. Obsidian settings belong in `starter/.obsidian/`, not the repository root.
- Keep vault creation and updates usable with the standalone Go executable. Install optional tool dependencies only when asked. Updates replace only the shared copies.
- Preserve unrelated edits and staged changes. Keep public examples fictional. The workshop directory is ignored scratch space and is not required to understand the project.
- Knowledge-note metadata does not apply to the repository's documentation or supporting files.

## Verification

Run `go test ./...` for setup changes. For maintenance tooling changes, run `python3 -m unittest discover -s tests -v` with PyYAML installed. Use temporary vaults and repositories. Do not install hooks here, download dependencies, or run package managers as part of the tests.

Check links and YAML/JSON after documentation changes. Assemble a temporary vault using the manual copy layout to check starter-relative links. Sync changed example vaults and check that a second run changes nothing.

Report what changed, what was checked, and any remaining limits. Leave draft choices clearly identified.
