# Properties and status

The [shared note fields](../vault-framework/notes.md) include `agent_edits` for editing permission and `decision_status` for standing decision records. This file defines additional choices for this vault.

A note without `status` is `active`. The starter uses the following values.

| Value | Meaning |
| --- | --- |
| `active` | The note is being worked on |
| `done` | The planned work on the note is complete |
| `abandoned` | The subject or idea is no longer being pursued |

A finished note can still need correction later. Record a change to an approved decision instead of silently replacing it.

Edit these values if the vault needs a different workflow. Document other local fields here, including which notes require them.
