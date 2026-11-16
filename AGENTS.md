# Working on vault-standards-spec

## Purpose

This repository develops the owner's personal standard for setting up and maintaining Git-backed knowledge vaults with humans and agents. It will contain conventions and supporting assets such as templates, starter files, examples, and potentially scripts or skills.

Public hosting is intended to simplify access. Design for the owner's preferences and workflows; flexibility serves the owner. Supporting other users is outside the project's scope.

Keep the core standard and tooling editor-agnostic. Obsidian is the owner's preferred vault editor; its configuration, including `.obsidian/`, belongs in vault template/sample directories. The standards repository root has no `.obsidian/` directory. Any runtime dependencies for future scripts must be chosen explicitly.

## Current stage and collaboration

The standard is in early development. Expect rapid revisions. Keep these instructions practical and provisional; revisit change restrictions when the owner considers the standard ready for version 0.1.

- Discuss unresolved consequential choices before establishing requirements. Present a concrete recommendation and distinguish it from an approved decision.
- Carry out approved work and routine implementation or wording choices autonomously. Changes to an early decision are normal; update affected guidance when the owner revises it.
- Keep this repository's development instructions distinct from instructions and conventions intended for consuming vaults. Vault note schemas do not automatically apply to every file here.
- Keep this file focused on project context and working rules. As detailed specifications are approved, put their contracts in the relevant documents and link them here rather than duplicating them.

## Sources and working material

The owner's current instructions take precedence over earlier design material. Treat approved committed specifications as the durable record as they develop. Separate settled decisions from proposals and open questions.

`standard-workshop-files/` is an uncommitted dumping ground for handoffs, historical vault files, and working material. When researching a design choice, consult relevant material there if available. Its absence must not prevent work on the repository. Preserve useful agreed context in committed documents rather than relying on workshop files as the only record.

Historical instructions and templates can contradict each other or later decisions. Reuse their useful substance without silently restoring superseded rules. The baseline below incorporates decisions made after the original handoff.

## Vault design baseline

- Give human knowledge management and agent access to durable context equal weight. Humans and agents maintain the same canonical notes.
- Use Git, ordinary Markdown, and YAML as durable formats. Prefer relative Markdown links and compatibility with Obsidian Properties and Bases.
- Maintain one shared standards repository. Each consuming vault is an independent Git repository with a copied standards snapshot. Continuous upstream synchronization is unnecessary.
- Separate personal and work vaults according to access, ownership, hosting, and sensitivity. Keep work material on approved infrastructure and use nonconfidential examples here.
- Let ordinary top-level vault directories define knowledge scopes with flexible nesting. Create structure when useful. Document types can occur across scopes, without required areas/projects wrappers or tags mirroring every path segment.
- Agents discover accessible vaults through user-level instructions, read the selected vault's local instructions, and search existing notes before creating new ones. Indexes supplement direct search.
- Prefer updating canonical notes and linking related information. A duplicate generated wiki, dedicated retrieval service, sync daemon, hard locking system, and heavy plugin stack are unnecessary.
- Use original code, tests, documentation, or system evidence for claims about current software behavior. Vault notes may be authoritative records of original decisions and preferences. Surface disagreements and distinguish evidence from assumptions.

## Capture and note properties

- `inbox/` holds raw captures and notes still in infancy. Notes tagged `thought-bubbles` also belong in `inbox/`; a separate ideas or thought-bubbles directory is unnecessary.
- Thought bubbles retain their iterative, speculative character. They can remain indefinitely, develop into another document, or be abandoned without forced promotion or deletion.
- Inbox notes and thought bubbles can lack ordinary structure and metadata. Exclude them from indexes by default; agents can search and read them directly.
- Normal structured notes use `tags` and a short, human- or agent-authored `description`. Tags can establish metadata, structure, and placement requirements; the detailed registry remains open.
- `date_created` is optional and useful, especially for distinguishing similarly titled tickets. Obsidian templates can populate it. Preserve an existing creation date when editing or moving a note.

## Directory indexes and automation

The desired index and automation behavior is still to be implemented and evaluated:

- Each configured top-level vault directory has an `index.md` covering eligible notes in that directory and its descendants.
- Group entries into sections by subdirectory and show where each note resides through paths and usable relative links. Include descriptions and useful configured metadata such as `ticket_id`.
- Make displayed properties and tags, note inclusion and exclusion, and indexed locations configurable. Support tag filtering, including exclusion of `thought-bubbles`, independently of where a note resides.
- Derive index listings from the notes and configuration so regeneration is straightforward. Keep the notes authoritative for their content and metadata.
- One-time setup per checkout or machine is acceptable. Aim for ordinary human and agent workflows to maintain derived information automatically afterward. Agent-assisted index updates are an acceptable fallback while automation develops.
- Explore a Git pre-commit hook for `date_updated`. Adopt it only if routine use is seamless; Git history is sufficient otherwise. An update date records editing, not independent verification of a claim.
- When implementing commit automation, preserve the user's staged and unstaged changes. Test the supported commit workflows before claiming the setup is seamless.

## Work records and evidence

- Keep a work item's Overview and final Completion Criteria in its main note. Use companions only when helpful. Separate required outcomes from acceptance verifications, with useful evidence in Markdown bullets.
- Check criteria only when evidence supports them; failed, blocked, and unrun checks stay unchecked. Research work is verified through its agreed outputs and suitable investigation, without artificial software tests.
- Execution plans track task progress separately from acceptance criteria. Keep stable increasing task IDs, retain cancelled tasks with strikethrough, and assess each task against its own deliverable. A coordinator owns the shared checklist; recheck current state when resuming.
- Preserve authored intent, decisions, useful history, and unrelated changes. Official work trackers remain official; publishing or editing their records requires an explicit user request.

## Decisions still open

Do not infer a complete specification from this baseline. Detailed tag and property contracts, closure and status semantics, document-type requirements, local overrides, filenames and heading links, reserved infrastructure directories, starter contents, index configuration format, script runtimes, hook mechanics, installation and upgrade details, and the version 0.1 change policy remain to be designed. Optional skills and OKF export are possibilities, not promised deliverables.
