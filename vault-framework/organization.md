# Organization

## Directories

Top-level directories such as `engineering/` or `home/` group knowledge by subject. Nest them as needed. A note can have one main home and links from other subjects.

| Directory | Purpose |
| --- | --- |
| `inbox/` | Raw captures and thought bubbles; included in the starter |
| `vault-framework/` | The versioned framework copy |
| `guidelines/` | Guidance for the whole vault |
| `<scope>/guidelines/` | Guidance for that scope |
| `templates/` | Note templates chosen for the vault |
| `attachments/` | Attachments, when needed |
| `vault-tools/` | Optional maintenance tools |
| `.obsidian/` | Optional editor settings |

Other top-level directories are knowledge scopes. Each vault decides where document types belong. Tags can guide placement without repeating the directory path.

## Guideline layers

Guidance builds in this order:

1. `vault-framework/` sets the shared structure and principles.
2. Root `guidelines/` defines vault-wide choices for tags, properties, organization, and workflows.
3. A scope's `guidelines/` adds or refines guidance for that scope. Nested scopes can add another layer.

Read the applicable layers from the framework down to the most specific scope. Each layer builds on the one above it. Raise conflicts instead of silently ignoring a rule or changing the framework copy.

Link the root guidance from `AGENTS.md`. Keep scoped guidance in the scope's `guidelines/` so agents can find it by following the directory path.

## Inbox

`inbox/` holds raw captures and early ideas. Use `thought-bubbles` for ideas still being worked out. These notes can lack normal structure and metadata, and are excluded from indexes by default.

Review the inbox during maintenance. Turn useful material into structured notes or tickets where appropriate. Remove abandoned ideas, keeping a short reason when it would help later. Local guidelines define who handles this work and what sources to retain.

## Framework versions

The copied folder includes a `VERSION` file. Keep it with the framework and leave it unchanged during normal vault work.

Framework changes belong in the framework repository. Review a new version before replacing the vault's copy. Local choices remain in root or scoped guidelines.

## Indexes and tools

Each indexed top-level directory has an `index.md` listing notes throughout its subtree. Sections group entries by subdirectory and show paths, descriptions, and selected properties. The vault controls inclusion and display settings.

Indexes copy metadata from notes for navigation. Inbox notes, the framework copy, and root or scoped guidelines are supporting files and are excluded by default.

The optional Python tool generates indexes without Git. Vaults using Git can also enable a hook for staged index and date updates. Setup and configuration are described in the tool's README. The tool maintains notes and indexes; it does not create a vault or copy framework files.
