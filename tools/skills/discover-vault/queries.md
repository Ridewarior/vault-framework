# Catalog queries

Use `sqlite3 -readonly -json "$catalog" "SELECT ..."` with the database path reported by sync. Use the full executable path in the sync result's `sqlite3` field when invoking the CLI. Quote SQL string literals by doubling single quotes. When using arbitrary text as an FTS5 phrase, also double embedded double quotes inside the FTS5 phrase.

## Schema version 1

Check the version with `PRAGMA user_version;`.

| Table | Fields |
| --- | --- |
| `notes` | `id`, vault-relative `path`, top-level directory `subject` (NULL for root notes), `title`, `description`, `date_created`, `date_updated`, `ticket_id` as text, `metadata_json`, and `content_hash` |
| `properties` | Note `path`, property `name`, zero-based `position`, and `value_json`. A list has one row per item. Scalars have one row. |
| `tags` | A view of distinct note `path` and whole YAML `tag` |
| `note_text` | FTS5 table with `rowid` matching `notes.id`, and searchable `path`, `title`, `description`, and `body` |
| `coverage` | Affected vault-relative `path`, `kind` (`metadata` or `scan`), and `detail` |

Dates use `YYYY-MM-DD` when provided in that format. `metadata_json` holds parsed frontmatter including vault-local fields, or `{}` when there is no frontmatter. NULL indicates a metadata gap. Use `json_extract(metadata_json, '$.status')` for a field such as status. Check `coverage` for inaccessible paths before using cached rows. Join FTS by row ID to include other note fields.

Use the indexed `properties` table to look up arbitrary field values and list members. For example, `SELECT DISTINCT path FROM properties WHERE name = 'related_tickets' AND value_json = json_quote('PLUS-318');` finds references even if the ticket lives outside the vault. List positions keep repeated values in order. For an empty list, an explicit null, or a missing field, use `json_type(metadata_json, '$.related_tickets')` on notes with readable metadata. Those cases return `array`, `null`, and SQL NULL respectively.

For a YAML boolean, use `value_json = 'true'` or `value_json = 'false'`. SQLite represents SQL `TRUE` as the number 1. For numeric comparisons, filter by the JSON type and compare the parsed number. This also handles different exponent formats.

```sql
SELECT DISTINCT path FROM properties
WHERE name = 'estimate'
  AND json_type(value_json) IN ('integer', 'real')
  AND json_extract(value_json, '$') = 1.0e+20;
```

## Ticket ID and title

```sh
sqlite3 -readonly -json "$catalog" "
SELECT path, title, description, date_created
FROM notes
WHERE subject = 'catalog' AND ticket_id = '42'
ORDER BY path;"
```

Quote a ticket ID in YAML if it has leading zeros. When there is no ticket ID, try `instr(lower(title), 'plus') > 0`, or the same expression with `description` or `path`. Dates can help sort similar candidates. Read the work item's links for companions with no ticket ID or date.

## Tags

For `work` and its descendants, compare the whole tag and the prefix including the slash. For a negative filter, change the tag subquery from `EXISTS` to `NOT EXISTS`. Keep the metadata and scan checks in either form.

```sh
sqlite3 -readonly -json "$catalog" "
SELECT n.path, n.title
FROM notes AS n
WHERE n.metadata_json IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM coverage AS c
    WHERE c.kind = 'scan'
      AND (n.path = c.path OR substr(n.path, 1, length(c.path) + 1) = c.path || '/')
  )
  AND EXISTS (
    SELECT 1 FROM tags AS t
    WHERE t.path = n.path
      AND (t.tag = 'work' OR substr(t.tag, 1, length('work') + 1) = 'work/')
  )
ORDER BY n.path;"
```

## Ranked full-text search

```sh
sqlite3 -readonly -json "$catalog" "
SELECT n.path, n.title, snippet(note_text, 3, '[', ']', ' ... ', 16) AS excerpt
FROM note_text JOIN notes AS n ON n.id = note_text.rowid
WHERE note_text MATCH 'search AND feedback' AND n.subject = 'catalog'
ORDER BY bm25(note_text, 2.0, 4.0, 2.0, 1.0), n.path
LIMIT 20;"
```

Run broader terms without the subject filter when the subject is unclear. Check excerpts against the saved Markdown. [SQLite CLI options](https://sqlite.org/cli.html#command_line_options) · [FTS5 queries](https://sqlite.org/fts5.html#full_text_query_syntax)
