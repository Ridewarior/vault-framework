# Examples

These examples use invented notes, dates, and ticket identifiers. They do not represent real approvals or test results.

The personal example shows references, research, a decision, and inbox captures. Try asking "Why did I stick with that editor?" The [editor note](personal/engineering/editors/is-it-worth-renewing.md) records what the owner values and what still bothers them. Renewal is open. The [standing decision](personal/engineering/decisions/plain-text-storage.md) explains a separate constraint that would apply even if they switched editors.

For a work example, try "Why did we suggest trying another term when there were no results?" The [catalog entry point](work/catalog/README.md) leads to the ticket's reasoning and an unresolved question, even if you have forgotten the ticket number. The [work starter additions](work/README.md) provide the matching local guidelines and templates.

Follow the [setup guide](../docs/setup.md) to create a vault, then copy any example material you want to try.

Each includes an index configuration. Regenerate the sample indexes with:

```sh
python tools/vault.py --vault examples/personal index
python tools/vault.py --vault examples/work index
```

The generated indexes show paths and subdirectory sections. Inbox notes are omitted so the examples also demonstrate direct capture without metadata.
