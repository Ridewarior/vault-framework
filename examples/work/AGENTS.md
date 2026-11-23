# Working in this work vault

These sample instructions refer to an assembled work vault. Adapt them to its actual tracker and subjects.

Read the vault README and [local guidelines](guidelines/README.md). Use the shared framework in `vault-framework/` for common principles, and keep that copy unchanged.

For the sample catalog subject, start at `catalog/README.md`. It identifies where project rules live. Read scoped `guidelines/` along the directory path for how to document the work. Apply the layers in order and surface conflicts.

Open Markdown directly when you know the path. For local discovery, use `vault-tools/skills/discover-vault/SKILL.md` if the optional tools are installed. Sync once, then query the reported catalog with `sqlite3 -readonly`. Use the ticket ID if given. Otherwise look in the subject and search titles, descriptions, and paths for remembered words. A date can narrow candidates, but companion notes may be undated. Search the Markdown directly if the catalog is unavailable or results miss likely notes.

Open the current ticket and any relevant companions before using them. Check original code or system evidence before claiming current behavior.

For ticket work, follow [work items](guidelines/work-items.md) and [completion criteria](guidelines/completion-criteria.md). Keep the agreed requirements in the main note. Check a criterion only when supporting evidence exists.

Use [execution plans](guidelines/execution-plans.md) for persistent task progress. Keep IDs stable and preserve cancelled tasks with strikethrough. One coordinator owns a shared parent checklist.

Follow [Notes and upkeep](vault-framework/notes.md) for `agent_edits`, pruning, and standing decisions. Keep useful ticket findings and implementation choices with the ticket. Look in the subject's `decisions/` for an owner-designated standing decision. Ask before treating a ticket choice as a rule for other work. Posting to the tracker requires a user request.

Process the inbox during maintenance. Turn useful captures into notes or work items and remove abandoned ideas when the task allows it. Follow the vault's storage and access rules when using tools or sharing information.
