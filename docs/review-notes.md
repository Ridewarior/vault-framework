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
- Setup remains manual. Installer ideas are kept in the repository's `docs/` directory.

- The framework is consolidated into an overview, organization, and notes guide. Its `VERSION` file identifies the copied version.
- Guidelines layer from the framework through root guidance to scoped guidance.
- The Python tool maintains indexes and dates. Vault assembly remains a manual copy step.

## Still open

Source and verification fields and cross-viewer heading links remain open before 0.1.

Tag registries, extra status values, work-note requirements, and subject-specific organization are vault decisions. Examples provide choices without making them framework requirements.

Python, PyYAML, JSON configuration, and hook behavior remain optional implementation choices. Other operating systems and Git clients still need testing.
