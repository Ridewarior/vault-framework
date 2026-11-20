# Vault framework

I want to be able to ask "Why did I stick with that editor?" months after the conversation, even if I forget what I called the note. My agents and I keep the reasons, observations, and open questions together so either of us can find the answer. Sometimes the notes show what I tried and the question is still open.

The framework covers shared structure, note metadata, and maintenance principles. Each vault defines its own subjects, tags, workflows, and agent instructions. Vaults choose their storage and sync method. This repository uses Git.

I use Obsidian, so the starter includes optional settings for it. The Markdown files and core rules work without Obsidian.

## In this draft

| Location | Contents |
| --- | --- |
| [Framework](framework/README.md) | Shared principles and conventions |
| [Starter](starter/README.md) | A reserved inbox, editable local guidelines, general templates, and sample agent instructions |
| [Examples](examples/README.md) | Personal notes and an optional work-vault setup |
| [Setup and updates](docs/setup.md) | Create or update a vault with the Go wizard |
| [Tool guide](tools/README.md) | Optional indexes and Git hook |
| [Review notes](docs/review-notes.md) | Recent decisions and open choices |

The source folders `framework/` and `tools/` become `vault-framework/` and `vault-tools/` inside a vault. Keep framework copies unchanged during normal use. A vault's `guidelines/` describes how to keep notes. Its root `AGENTS.md` directs agents working there.

## Use it

Run the setup executable with no arguments for a guided walkthrough. It includes the starter files. From a source checkout with Go 1.23 or newer, run `go run ./installer`.

After the first published release, use the [download and launch commands](docs/setup.md) on a fresh device. The [setup skill](skills/setup-vault/SKILL.md) helps an agent create a vault and adapt its local guidelines. See the [release guide](docs/releases.md) to build and publish downloads.

This is an early draft toward 0.1. Read [AGENTS.md](AGENTS.md) before agent work on the repository. The repo is public for convenient access; its choices follow my own needs.
