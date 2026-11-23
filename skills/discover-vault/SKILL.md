---
name: discover-vault
description: Discover Markdown notes in a vault by subject, ticket ID, date, tags, or text. Use for finding past decisions or locating a work item when its path is unknown.
---

# Discover vault notes

Open the Markdown directly when you know its path. For local discovery, run catalog sync once from the vault root using the prepared Python environment.

```sh
.venv/bin/python vault-tools/vault.py sync
```

On Windows use `.venv\Scripts\python.exe`. The sync output is JSON. Run the executable in its `sqlite3` field with `-readonly -json` and the `database` path. If `sqlite3` is null, use direct Markdown search until the local tools are prepared. Reuse the catalog for follow-up queries. Sync again if newer edits matter. The [query reference](queries.md) has the schema and examples.

For recall, find the subject and search for remembered words, including alternatives and reasons. For work in progress, use the exact ticket ID if you have it. Otherwise narrow by subject, title, description, path, and approximate date. Dates are optional. Widen a date filter if it hides likely notes or their companions. Open the current Markdown before using it as evidence or editing it.

Check sync's `coverage` before relying on a miss or a count. A `metadata` gap means text is searchable, but property and tag filters cannot classify that note. A `scan` gap may leave old results for a file or directory. Search those paths directly and report gaps that affect the answer. If sync fails, it reports whether a previous snapshot was found. Use direct Markdown search if the catalog is missing, the gap is unclear, or a query is unexpectedly empty. Include the inbox and other subjects when relevant.

For a vault available only on GitHub, open the intended branch and follow the subject's README and relative links. Use code search where it covers that branch. A miss there cannot establish absence. Cite the notes you opened and identify any search gap that affects the answer.
