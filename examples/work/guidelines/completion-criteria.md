# Completion criteria

Completion criteria describe what establishes that a work item is finished. Keep them in the main note and update them as the work becomes clearer.

## Functional requirements

State the required outcomes or deliverables. Preserve the agreed scope. Split a requirement when its parts can be assessed separately.

## Acceptance verifications

Describe the checks that establish those outcomes. Choose the method that fits, such as a test, browser check, code review, or research comparison. Keep the checks together rather than separating them by test technology.

```markdown
## Completion criteria

### Functional requirements

- [ ] Authorized users can access account settings.

### Acceptance verifications

- [ ] An unauthorized request is denied.
  - Method: API verification
  - Evidence: Pending execution.
```

A checked box means evidence supports the result. Pending, failed, blocked, and unrun checks stay unchecked. Writing a test does not prove it passed.

Record useful test results, source references, logs, screenshots, or environments below the check. Link lengthy evidence rather than copying it into the checklist.

Before calling the work complete, check that requirements and verifications are satisfied or that remaining exceptions were explicitly accepted.

## Research

Research is judged by its agreed questions and outputs. Sources, comparisons, experiments, or documented uncertainty can support the result. Runtime checks apply when the research includes running software.
