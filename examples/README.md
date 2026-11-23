# Examples

These examples use invented notes, dates, and ticket identifiers. They do not represent real approvals or test results.

The personal example shows references, research, a decision, and inbox captures. Try asking "Why did I stick with that editor?" The [editor note](personal/engineering/editors/is-it-worth-renewing.md) records what the owner values and what still bothers them. Renewal is open. The [standing decision](personal/engineering/decisions/plain-text-storage.md) explains a separate constraint that would apply even if they switched editors.

For a work example, try "Why did we suggest trying another term when there were no results?" The [catalog entry point](work/catalog/README.md) leads to the ticket's reasoning and an unresolved question, even if you have forgotten the ticket number. The [work starter additions](work/README.md) provide the matching local guidelines and templates.

Follow the [setup guide](../docs/setup.md) to create a vault, then copy any example material you want to try.

With the optional tools prepared, run catalog sync on either example from the repository root. Use the Python environment you prepared for the tools.

```sh
python tools/vault.py --vault examples/personal sync
python tools/vault.py --vault examples/work sync
```

The personal catalog includes the inbox captures and thought bubbles. In the work catalog, try looking up ticket 42 by ID and following its links to the undated discussion. The [query reference](../skills/discover-vault/queries.md) has examples for ticket IDs, nested tags, and full text.
