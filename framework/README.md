# Vault framework

This framework sets the shared structure for my knowledge vaults. Each vault defines its own subjects, tags, workflows, and agent instructions within that structure.

The current version is recorded in [VERSION](VERSION). This is an early draft. The version file travels with each framework copy so the vault can identify what it uses.

| Guide | Covers |
| --- | --- |
| [Organization](organization.md) | Directories, guideline layers, framework updates, and indexes |
| [Notes and upkeep](notes.md) | Properties, tags, status, templates, writing, and maintenance |

## Shared knowledge

Humans and agents use the same notes. Keep one main note for a subject, link related material, and update it as knowledge changes.

Use Markdown, simple YAML properties, and ordinary links so the files work across editors. Obsidian is a useful interface, but the framework does not depend on it.

A note may record an original decision, an old observation, or an untested idea. Make the difference clear. Check current software behavior against the relevant code, tests, documentation, or running system. Record disagreements between sources.

A vault supports a ticket system or work tracker already in use. It does not replace it.

## Storage and access

Each vault chooses its storage, sync, and access controls. Git is optional. The storage system provides security; folders within a vault do not restrict access.

What belongs in a vault depends on its purpose. Financial records may belong in a private personal vault, while work notes may need company-managed storage. Credentials and private keys belong in a secrets manager rather than plain-text notes.

## Agents and local guidance

Agents use the vault to find prior decisions, preferences, and relevant sources. Useful findings go back into the existing notes so later sessions can use them. Indexes help with discovery, while direct search covers material such as the inbox.

Each vault's `AGENTS.md` and guideline layers explain how to work there. Access to a note does not grant permission to publish it or change another system.

Keep the framework copy unchanged during normal vault work. Put local choices in the vault's guidelines. Optional tools can reduce upkeep, but the notes must remain usable without them.
