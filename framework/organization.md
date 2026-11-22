# Organization

## Directories

Top-level directories such as `engineering/` or `home/` group knowledge by subject. File new material directly in a subject folder when it fits. Add a subfolder when it groups material someone would look for together. A note can have one main home and links from other subjects.

| Directory | Purpose |
| --- | --- |
| `inbox/` | Raw captures and thought bubbles; included in the starter |
| `vault-framework/` | The versioned framework copy |
| `guidelines/` | How to keep notes across the vault |
| `<scope>/guidelines/` | How to keep notes about that subject |
| `decisions/` or `<scope>/decisions/` | Records of standing decisions for the vault or subject |
| `templates/` | Note templates chosen for the vault |
| `attachments/` | Attachments, when needed |
| `vault-tools/` | Optional maintenance tools |
| `.obsidian/` | Optional editor settings |

Other top-level directories are knowledge scopes. Tags can guide placement without repeating the directory path.

## Finding your way around a subject

The vault identifies each subject's entry point, such as a README, in its navigation or agent instructions. Use it to learn what the subject covers and where its authoritative material lives. Project rules usually live in the project repository. When the vault holds project rules, the entry point tells readers where to find them.

For the reasoning behind a standing decision, look first in `decisions/` at the root of the subject it governs. A project's records might live in `engineering/my-project/decisions/`. Vault-wide records live in the vault root's `decisions/`. The same folder can hold records about any aspect of its subject, including why its documentation guidelines changed. Create the folder when there is a record to file. Keep one record and link to it from other affected subjects.

## Guideline layers

Guidance builds in this order:

1. `vault-framework/` sets the shared structure and principles.
2. Root `guidelines/` defines vault-wide choices for tags, properties, organization, and workflows.
3. A scope's `guidelines/` explains how to document that subject. For example, it might say where to record ticket evidence. Nested scopes can refine those instructions.

Read the applicable layers from the framework down to the most specific scope. Each layer builds on the one above it. Raise conflicts instead of silently ignoring a rule or changing the framework copy.

Link the root guidance from `AGENTS.md`. Keep scoped guidance in the scope's `guidelines/` so agents can find it by following the directory path.

## Inbox

`inbox/` is a temporary home for captures you want to sort later. A recurring thought can live in its subject folder as soon as you know where it belongs, even if it stays open for months. Use `thought-bubbles` to find such ideas across folders. Look for them by text or tag when revisiting an open idea.

Review the inbox during maintenance. Turn useful material into structured notes or tickets where appropriate. Remove abandoned ideas, keeping a short reason when it would help later. Local guidelines define who handles this work and what sources to retain.

## Framework versions

The copied folder includes a `VERSION` file. Keep it with the framework and leave it unchanged during normal vault work.

Framework changes belong in the framework repository. Review a new version before replacing the vault's copy. You can update the framework and optional tools with the repository's setup command. Local choices remain in root or scoped guidelines.

## Discovery tools

Use subject entry points and authored links to browse. When a note's path is known, open the Markdown. For discovery across notes, the optional tool builds a local SQLite catalog from saved files. It includes captures and thought bubbles by default. Vaults can exclude paths.

Each device builds its own catalog outside the vault. Markdown stays authoritative. A Git vault can use optional hooks for staged dates and post-commit catalog refreshes. See the README in `vault-tools/` for setup and queries.
