---
name: setup-vault
description: Create a new vault with the vault-framework CLI and tailor its starter files to the owner's purpose and guidelines.
disable-model-invocation: true
---

Use the destination and intended use from the request. Ask about missing choices that affect setup, such as storage, Obsidian, or automatic indexes. A request for an index does not imply Git. Use the installed vault executable or build it from the framework checkout with Go. See `vault init --help` for flags.

Run `vault init PATH` with the chosen flags. Use a new or empty directory. If requested, run `vault prepare PATH` to install maintenance dependencies and add `--hook` for a Git hook. If Python is missing, explain how to resume preparation in the vault already created.

Personalize the installed README with the vault's purpose and known storage choices. Put organization, tags, and metadata rules in the installed `guidelines/`. Use the installed `AGENTS.md` for agent procedures and pointers to those rules. Keep the owner's wording where it conveys a preference. Leave unknown policies open. Add scoped guidelines or work templates only when the brief calls for them.

Read back the local files and check their links. Report the vault path, the choices applied, and anything that still needs setup. Framework and tool updates own the two shared folders, so keep personalized material outside them.
