# Review notes

## Changes from review

- Vaults choose their own storage. Git is required only for Git-based features.
- `vault-framework/` holds the unchanged framework copy. `vault-tools/` holds its optional tools. `guidelines/` holds local governance.
- The starter includes `inbox/` and editable local rules for tags, properties, and organization.
- Work-item rules, evidence checklists, execution plans, and their templates live in the optional work example.
- Agent procedures live in the sample `AGENTS.md`. The framework describes how agents use vaults.
- Captures can go straight into a subject folder. An open thought can stay there between sessions. During upkeep, agents can trim dead ends from working notes and keep old material that still explains a choice.
- `status` can apply to any note, with suggested values `active`, `done`, and `abandoned`.
- The repo uses `framework/` and `tools/`. The setup command copies them into vaults with the `vault-` prefix. It can update those copies separately from the starter.
- The framework is consolidated into an overview, organization, and notes guide. Its `VERSION` file identifies the copied version.
- Guidelines layer from the framework through root guidance to scoped guidance and cover how to document each subject. The vault identifies subject entry points and where authoritative project material lives.
- The optional `agent_edits` property expresses the owner's editing permission. The default is `auto`.
- Standing decisions belong in the owning subject's `decisions/`. The owner designates them. The short record and fuller technical template both preserve the reason for the choice and support supersession.
- Use `deprecated` when the owner retires an accepted decision without a replacement. The record keeps its original reasoning.
- SQLite discovery gives each vault one searchable catalog on each device.

## Local choices

Each vault chooses its source and verification fields alongside its tags, extra status values, and work-note requirements. Relative links to files are the portable default. Check any heading links in the viewers the vault uses.

## Testing before 0.1

Try SQLite preparation, sync, and a read-only query on macOS and Windows. Rehearse the note transfer in a separate copy of an existing vault. Compare the source and destination note lists, check links and attachments, and try a question whose answer is known. After an edit and a move, check that search finds the new text and path. A final sync should report no further changes.

## Possible updater review

Try giving an agent the GitHub link for the new framework version and asking it to compare the vault's layout and guidelines with that version. Ask for differences and file references so the owner can decide what to change. If this becomes a common task, the updater could print a review prompt with the version and relevant paths.
