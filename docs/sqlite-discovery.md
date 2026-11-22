# Finding vault notes with SQLite

New vaults use one searchable catalog for discovery. Each device that enables search builds its own SQLite database outside the synced vault. Markdown stays authoritative. The catalog includes inbox captures and thought bubbles by default. Vaults can define their own exclusions. Readers can still browse subject folders and authored READMEs. [Framework](../framework/README.md) · [Catalog setup and settings](../tools/README.md)

## Keep search current

When the owner enables local catalog tools, the wizard prepares SQLite on that device. Reuse a suitable sqlite3 executable or install one. Verify that the sync tool can build a temporary FTS5 table and that the CLI can query it. [Current device setup](setup.md) · [SQLite CLI](https://sqlite.org/cli.html) · [SQLite FTS5](https://sqlite.org/fts5.html)

The optional maintenance tool provides `vault.py sync`. It compares eligible Markdown paths, content hashes and selection settings with the last successful index. It creates a missing catalog, updates affected entries and leaves a current catalog alone. It reports the database path, counts of added, updated and removed notes, and paths with incomplete coverage.

Each framework release declares its catalog schema version, starting at 1. Sync records it in SQLite's `PRAGMA user_version`. A documentation change can keep the same number. When the schema changes, the release includes matching query examples. Sync rebuilds an older catalog from Markdown and asks for a tool update if it encounters a newer schema. Adding a vault-specific property requires only a normal sync. [SQLite user version](https://sqlite.org/pragma.html#pragma_user_version)

In a Git vault with hooks installed, the post-commit hook runs the same sync. It runs after staged timestamp maintenance and reads saved working files. Its outcome cannot reject the commit. Active work only needs a usable path to the note. Once the agent has that path, it can read each saved edit directly. [Git hooks](https://git-scm.com/docs/githooks) · [Git status](https://git-scm.com/docs/git-status) · [Existing hook behavior](../tools/README.md)

A watcher remains an option if another program needs an already-updated database seconds after each save, even when nobody searches. A cross-platform watcher also needs recovery scans. Linux can lose events if its queue fills, macOS can request a rescan after dropped events, and Windows can discard the change buffer. A timed refresh would also need per-device scheduling and would leave a gap between a save and the next run. [Linux inotify](https://man7.org/linux/man-pages/man7/inotify.7.html) · [Apple filesystem events](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/FSEvents_ProgGuide/UsingtheFSEventsFramework/UsingtheFSEventsFramework.html) · [Windows directory notifications](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-readdirectorychangesw)

Treat a move as an added path and a removed path, including the notes under a moved folder. Confirm the old path is gone before removing it. An unreadable folder or disconnected vault leaves that part of the scan incomplete. Retry it when accessible. Commit the path changes, metadata, tags, full-text rows and scan status together. A search then sees one committed version, even during a refresh. [SQLite transactions](https://www.sqlite.org/lang_transaction.html)

## Search during edits

Index saved note text with FTS5. A capture without frontmatter can appear by filename or body. If a note changes during a read, retry it or report the pending path. If the saved text has unfinished YAML, index the readable text and flag the path. Drop its previous metadata from filters until parsing succeeds. Other notes remain searchable. If the text itself cannot be read, flag that gap too. [Current frontmatter parser](../tools/vault.py) · [SQLite FTS5](https://www.sqlite.org/fts5.html)

Store each declared YAML tag whole. A filter for `work` matches `work` and descendants beginning with `work/`, including `work/feature`. It skips `workshop`. A filter for `feature` alone only finds a note that declares that tag or a descendant of it. This preserves what the author entered and follows the existing filter rule. [Framework tag rules](../framework/notes.md) · [Obsidian nested tags](https://obsidian.md/help/tags)

## One lookup rule for agents

The starter gives agents this workflow.

> If you know the path, open the Markdown file. When you need to discover notes locally, run sync once, then query the database path it reports with sqlite3 in read-only mode. Reuse that catalog for follow-up queries. Sync again if newer edits matter. To recall past work, search the subject's note text for remembered terms. To resume work, look up the ticket ID or narrow candidates by subject, title, description and date. Open the current file before editing. If sync reports a gap, check the affected paths. Without a catalog, follow the subject entry point and search Markdown directly.

For example, suppose someone asks what was decided on last week's Web Plus ticket. Narrow the search to the subject, use the approximate date to find the ticket, and search its notes for wording from the discussion. The date is a clue about the ticket. A linked questions-and-decisions note may be undated. Cite the recorded answers and identify any questions that remain open. [Example ticket](../examples/work/catalog/work/42-search-feedback/work-item.md) · [Linked questions and decisions](../examples/work/catalog/work/42-search-feedback/questions-and-decisions.md)

If someone asks for test cases for today's Plus ticket, use the exact ticket ID when supplied. Otherwise look for "Plus" in recent titles, descriptions and paths within the subject. Note dates are optional. Widen the search if a date filter hides likely matches. Once the ticket is identified, open its current Markdown, read the newly saved requirements and write the requested cases there. If several tickets still fit, confirm which one before editing. [Note properties](../framework/notes.md) · [Work-item guidance](../examples/work/guidelines/work-items.md)

The search skill documents the schema and read-only SQL examples for ticket IDs, nested tags and ranked full-text matches. Agents can run these or adapt the SQL with the standard CLI, using the form `sqlite3 -readonly -json "path/to/catalog.sqlite" "SELECT ..."`. The path and query here are placeholders. [SQLite CLI options](https://sqlite.org/cli.html#command_line_options)

Sync should report incomplete coverage when a file changes during the check and cannot be reread, a path is inaccessible, or invalid metadata could affect the answer. For example, a tag count can say "3 matches. 1 draft has unreadable tags." Keep that draft out of both positive and negative tag filters. Search the affected paths directly. If the gap is unknown, the database is missing, or a search comes up unexpectedly empty, search Markdown across the scope of the question, including other subjects and the inbox when relevant.

On GitHub, browse the intended branch, open its subject README and follow relative links. GitHub code search can help on the default branch, but a miss there cannot establish that a note is absent. Report what was searched and any gap that affects the answer. [GitHub search limits](https://docs.github.com/en/search-github/github-code-search/about-github-code-search#limitations)

When evaluating performance on a working vault, time sync and a subsequent SQLite query together. Compare a first build, an unchanged search and a search after an edit. Include cold files when measuring a slower drive.
