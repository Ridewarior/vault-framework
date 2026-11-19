# Review notes

The draft now separates the framework from rules owned by each vault.

## Changes from review

- Vaults choose their own storage. Git is required only for Git-based features.
- `vault-framework/` holds the unchanged framework copy. `vault-tools/` holds its optional tools. `guidelines/` holds local governance.
- The starter includes `inbox/` and editable local rules for tags, properties, and organization.
- Work-item rules, evidence checklists, execution plans, and their templates live in the optional work example.
- Agent procedures live in the sample `AGENTS.md`. The framework describes how agents use vaults.
- Inbox maintenance should produce useful notes or remove abandoned ideas.
- `status` can apply to any note, with suggested values `active`, `done`, and `abandoned`.
- The repo uses `framework/` and `tools/`. The setup command copies them into vaults with the `vault-` prefix. It can update those copies separately from the starter.
- The framework is consolidated into an overview, organization, and notes guide. Its `VERSION` file identifies the copied version.
- Guidelines layer from the framework through root guidance to scoped guidance.
- The maintenance tool reports generated indexes left behind when a vault changes its index roots.

## Still open

Source and verification fields and cross-viewer heading links remain open before 0.1.

Tag registries, extra status values, work-note requirements, and subject-specific organization are vault decisions. Examples provide choices without making them framework requirements.

Python, PyYAML, JSON configuration, and hook behavior remain optional implementation choices. Other operating systems and Git clients still need testing.

## Possible updater review

Try giving an agent the GitHub link for the new framework version and asking it to compare the vault's layout and guidelines with that version. Ask for differences and file references so the owner can decide what to change. If this becomes a common task, the updater could print a review prompt with the version and relevant paths.
