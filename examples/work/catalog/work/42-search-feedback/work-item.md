---
tags:
  - work/feature
description: Clear feedback for catalog searches with no results.
ticket_id: 42
status: active
date_created: 2026-11-15
date_updated: 2026-11-15
---

# Search feedback

## Overview

Show a useful message when a catalog search returns no matches. The current implementation has not been checked.

## Supporting notes

- [Questions and decisions](questions-and-decisions.md)
- [Working notes](working-notes.md)
- [Execution plan](execution-plan.md)

## Completion criteria

### Functional requirements

- [ ] An empty successful search produces an understandable no-results message.
- [ ] A failed request remains distinguishable from a successful search with no matches.

### Acceptance verifications

- [ ] A successful empty response displays the agreed message.
  - Method: Browser or component verification, selected after implementation review.
  - Evidence: Pending. No check has been executed.
- [ ] A failed response follows the agreed error behavior.
  - Method: API and UI verification as appropriate.
  - Evidence: Pending. No check has been executed.
