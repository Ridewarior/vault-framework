---
tags:
  - decision
description: Why engineering notes use Markdown with simple YAML properties.
decision_status: accepted
date_created: 2026-11-15
---

# Plain-text storage

## Context

Engineering notes need to open in several editors. I also want an agent to be able to search the same files.

## Decision

On November 15, 2026, I chose Markdown with simple YAML properties for my engineering notes. This replaces my [earlier choice to use the editor's notebook](use-editor-notebook.md).

## Rationale and alternatives

The notebook made it easy to capture a note alongside code, but reading those notes from another editor required an export. I wanted to search the originals from either editor.

## Consequences

Keep metadata and links portable. The living [reference](../editor-preferences.md) records the resulting preference.
