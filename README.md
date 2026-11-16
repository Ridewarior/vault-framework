# Vault standards

My personal standard for organizing and maintaining Git-backed knowledge vaults, with shared conventions for me and the agents I use.

I want to record useful knowledge once and make it easy to find again. That includes references, research, decisions, preferences, and the working context that would otherwise disappear between projects or agent sessions. Humans and agents should read and maintain the same notes.

I use Obsidian for editing and browsing. The core standard stays editor-agnostic, using Markdown, YAML properties, relative links, and Git. Obsidian configuration will live in vault templates and samples.

This repository is intended to be public for convenient access. Its design follows my own workflows and preferences.

## Current state

Early development, working toward an initial 0.1 version. The repository currently contains project guidance and Git configuration. The detailed specification, starter vault, templates, and automation are still to be built. Decisions can change quickly during this stage.

## How vaults should work

- Each vault is an independent Git repository containing a snapshot of the shared standard. Personal and work vaults have separate access and storage boundaries.
- Top-level directories represent knowledge scopes, with flexible nesting and document types used wherever they fit.
- Raw captures and notes tagged `thought-bubbles` live in `inbox/`. They can remain informal while their usefulness and direction develop.
- Structured notes use tags and descriptions to support discovery. Directory indexes will list eligible notes recursively, grouped by subdirectory, with paths and configurable metadata.
- Agents search existing notes before creating new ones, preserve useful decisions and evidence, and check original sources when establishing current software behavior.

The notes remain authoritative for their content. Indexes provide navigation derived from those notes. Git records changes over time.

## Planned supporting assets

The standard will be accompanied by reusable note templates, a starter/sample vault, and examples. Small scripts or agent skills may support recurring work where they reduce upkeep.

Automation is a design goal still to be evaluated. In particular, configurable index generation and a possible `date_updated` pre-commit hook should fit ordinary editing and committing after one-time setup. Git history is sufficient if timestamp automation cannot meet that goal. `date_created` remains optional and can be populated through note templates.

## Working on this repository

Read [AGENTS.md](AGENTS.md) for the current design baseline, unresolved choices, and instructions for agent sessions. Detailed specification documents will be added as the design develops.

The local workshop directory contains temporary design inputs and scratch material. It is excluded from Git and is unnecessary for reading the committed project documentation.
