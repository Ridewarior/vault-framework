# Properties and status

Work items use the common note fields and can add:

| Property | Use |
| --- | --- |
| `ticket_id` | The actual identifier from the tracker, in its original format |
| `related_tickets` | A list of related identifiers |
| `status` | The current note state, including whether work on it is finished |

Identifiers are optional when there is no external ticket. Leave unknown values out.

For this example, `active`, `done`, and `abandoned` describe progress. They can apply to any note, not just a ticket. Extend or replace these values for the actual vault.
