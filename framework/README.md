# Vault framework

I use these vaults to pick up a question long after I have forgotten the conversation or the name of the note. People and agents keep enough context for a later reader to find what we learned, why we made a choice, and what we left open. Each vault defines its own subjects and ways of keeping notes.

The current version is recorded in [VERSION](VERSION). This is an early draft. The version file travels with each framework copy so the vault can identify what it uses.

| Guide | Covers |
| --- | --- |
| [Organization](organization.md) | Directories, guideline layers, framework updates, and indexes |
| [Notes and upkeep](notes.md) | Properties, agent edits, standing decisions, and what to keep |

## Shared knowledge

Humans and agents use the same notes. Update the note that already answers a question and link related material. Agent working notes can hold the context another session would otherwise have to reconstruct.

Use Markdown, simple YAML properties, and ordinary links so the files work across editors. Obsidian is a useful interface, but the framework does not depend on it.

A note may record an original decision, an old observation, or an untested idea. Make the difference clear. Check current software behavior against the relevant code, tests, documentation, or running system. Record disagreements between sources.

A vault supports a ticket system or work tracker already in use. It does not replace it.

## Storage and access

Each vault chooses its storage, sync, and access controls. Git is optional. The storage system provides security; folders within a vault do not restrict access.

What belongs in a vault depends on its purpose. Financial records may belong in a private personal vault, while work notes may need company-managed storage. Credentials and private keys belong in a secrets manager rather than plain-text notes.

## Agents and local guidance

Search in the words someone might remember, such as a symptom, a rejected option, or a question. Follow links to the reasons and sources. When the notes show only what someone tried, say which choices are still open. An agent can follow a convention apparent in nearby work. The owner decides whether it becomes a standing rule or preference.

Each vault's `AGENTS.md` and guideline layers explain how to work there. Access to a note does not grant permission to publish it or change another system.

Keep the framework copy unchanged during normal vault work. Put local choices about keeping notes in the vault's guidelines. Optional tools can reduce upkeep, but the notes must remain usable without them.
