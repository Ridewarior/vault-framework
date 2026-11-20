---
tags:
  - sub-doc/decisions
description: Why an empty catalog search suggests trying another term. Error handling is still open.
---

# Questions and decisions

Parent: [Search feedback](work-item.md).

## Open questions

- [ ] Should existing error handling be reused or changed?

## Decisions

For this search screen, use "No matches. Try another search term." The request succeeded and changing the query is something the reader can do. Reserve failure messages for requests that actually failed. We only considered wording for this ticket.
