# Vault framework

A framework for my knowledge vaults and the agents that use them.

The framework covers shared structure, note metadata, and maintenance principles. Each vault defines its own subjects, tags, workflows, and agent instructions. Vaults choose their storage and sync method. This repository uses Git.

I use Obsidian, so the starter includes optional settings for it. The Markdown files and core rules work without Obsidian.

## In this draft

| Location | Contents |
| --- | --- |
| [Framework](vault-framework/README.md) | Shared principles and conventions |
| [Starter](starter/README.md) | A reserved inbox, editable local guidelines, general templates, and sample agent instructions |
| [Examples](examples/README.md) | Personal notes and an optional work-vault setup |
| [Manual setup](docs/manual-setup.md) | How to copy the files into a vault |
| [Tool guide](vault-tools/README.md) | Optional indexes and Git-hook upkeep |
| [Review notes](docs/review-notes.md) | Recent decisions and open choices |

The copied framework lives in `vault-framework/`. Keep it unchanged during normal use. Its optional tools live in `vault-tools/`. A vault's own rules live in `guidelines/` and its root `AGENTS.md`.

## Use it

Download or clone this repository, then follow [manual setup](docs/manual-setup.md). Choose the templates and examples that fit the vault. A personal vault does not need the work-item rules.

The optional Python tool creates recursive directory indexes. A vault using Git can also enable a hook for index and date upkeep. Installer automation is [deferred](docs/future-setup-automation.md).

This is an early draft toward 0.1. Read [AGENTS.md](AGENTS.md) before agent work on the repository. The repo is public for convenient access; its choices follow my own needs.
