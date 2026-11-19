# Notes and upkeep

## Properties

Use YAML frontmatter for note metadata. Simple values and lists work well across editors.

| Property | Use |
| --- | --- |
| `tags` | Required on structured notes. Use a nonempty list of lowercase tags. |
| `description` | Required on structured notes. Briefly describe what the note contains. |
| `title` | Optional display title. Tools can use the first heading or filename instead. |
| `date_created` | Optional creation date, useful for distinguishing similar notes. |
| `date_updated` | Optional edit date, which maintenance tools can update. |
| `status` | Optional progress or completion state for any kind of note. |

Inbox notes and thought bubbles can omit these fields. Framework files, guidelines, templates, and tooling are also exempt.

Use `YYYY-MM-DD` for dates. Preserve a known creation date when moving or editing a note, and leave unknown dates out. An edit date records a text change, not a check that the information is still correct.

```yaml
---
tags:
  - resource
description: How the backup rotation works and where its settings live.
status: active
date_created: 2026-11-15
---
```

Each vault defines its tag vocabulary and extra fields in its guidelines. Ticket identifiers and source details depend on the vault's needs.

## Status

These values are useful starting points:

| Value | Meaning |
| --- | --- |
| `active` | The note or subject is being worked on. |
| `done` | The planned work is complete. |
| `abandoned` | The subject or idea is no longer being pursued. |

A vault can extend these values and define what they mean for later edits. Status can apply to research, references, ideas, or work items. Finishing a note does not prove its information will stay current.

## Tags

Use lowercase tags and `/` when one tag is a subtype of another. A parent-tag filter matches its children, so `research` also matches `research/backups`.

Each vault should keep its registry in root or scoped guidelines. Explain which tags affect properties or placement and which help with search. `thought-bubbles` identifies early ideas in `inbox/`.

Tags do not have to mirror folders or name every subject mentioned in a note. Put dates and identifiers in properties when they represent values rather than categories.

## Templates and writing

Each vault chooses its document types and templates. The general starter includes captures, references, research, meetings, and decisions. Work-item notes and execution plans are optional additions from the work example.

Replace template guidance with real content and remove unused sections. Obsidian's core Templates plugin can fill `{{title}}` and `{{date}}`; agents can fill the same templates directly.

Use clear, complete sentences and relative Markdown links. Keep enough context for a later reader to understand the note without the original conversation. Check links after moving files. Filename and formatting choices belong to the vault.

## Maintenance

Update references when new information changes them, and keep useful decision history. When a decision changes, record the new choice and its reason.

Process inbox material regularly. Move useful ideas into structured notes or tickets where the vault uses them. Remove abandoned ideas when local rules allow it, leaving a reason when it is worth remembering.
