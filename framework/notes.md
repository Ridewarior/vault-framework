# Notes and upkeep

## Properties

Use YAML frontmatter for note metadata. Simple values and lists work well across editors.

| Property | Use |
| --- | --- |
| `tags` | Required on structured notes. Use a nonempty list of lowercase tags. |
| `description` | Required on structured notes. Briefly describe what the note contains. |
| `title` | Optional display title. Tools can use the first heading or filename instead. |
| `date_created` | Optional creation date, useful for distinguishing similar notes. |
| `date_updated` | Optional edit date, which maintenance tools can update. |
| `status` | Optional progress or completion state for any kind of note. |
| `agent_edits` | Optional editing permission. The default is `auto`. |
| `decision_status` | Records the owner's ruling on a proposal and whether it still applies. See Standing decisions below. |

Inbox notes and thought bubbles can omit these fields. Framework files, guidelines, templates, and tooling are also exempt.

Use `YYYY-MM-DD` for dates. Preserve a known creation date when moving or editing a note, and leave unknown dates out. An edit date records a text change, not a check that the information is still correct.

```yaml
---
tags:
  - resource
description: How the backup rotation works and where its settings live.
status: active
date_created: 2026-11-15
---
```

Each vault defines its tag vocabulary and extra fields in its guidelines. Each vault decides whether to use fields for sources, verification, or ticket identifiers.

## Agent edits

| Value | How to edit the note |
| --- | --- |
| `auto` or omitted | Use the task and the note's purpose to judge whether an edit is appropriate. A request to recall an editor comparison calls for reading it. A request to maintain the comparison authorizes edits. |
| `ask` | Get the owner's permission before editing the note, including changing or removing this property. A direct request to edit that note grants permission for the requested change. Ask before including it in a general cleanup. |
| `always` | An agent may edit the note freely as it works. An agent can set this on working notes it creates for its own session or a handoff. |

Respect the current permission when pruning, merging, or removing a note. Permission to edit the text leaves the choice of standing preferences and rules with the owner.

## Status

These values are useful starting points:

| Value | Meaning |
| --- | --- |
| `active` | The note or subject is being worked on. |
| `done` | The planned work is complete. |
| `abandoned` | The subject or idea is no longer being pursued. |

A vault can extend these values and define what they mean for later edits. Status can apply to research, references, ideas, or work items. Finishing a note does not prove its information will stay current.

## Tags

Use lowercase tags and `/` when one tag is a subtype of another. A parent-tag filter matches its children, so `research` also matches `research/backups`.

Each vault should keep its registry in root or scoped guidelines. Explain which tags affect properties or placement and which help with search. `thought-bubbles` identifies ideas still taking shape in the inbox or a subject folder.

Tags do not have to mirror folders or name every subject mentioned in a note. Put dates and identifiers in properties when they represent values rather than categories.

## Templates and writing

Each vault chooses its document types and templates. The general starter includes captures, references, research, meetings, and decisions. Work-item notes and execution plans are optional additions from the work example.

Replace template guidance with real content and remove unused sections. Obsidian's core Templates plugin can fill `{{title}}` and `{{date}}`; agents can fill the same templates directly.

Use clear, complete sentences and relative Markdown links to files. When a link needs to point to a heading, check it in the viewers the vault uses. Keep enough context for a later reader to understand the note without the original conversation. Check links after moving files. Filename and formatting choices belong to the vault.

## Standing decisions

A standing decision guides future choices within a stated scope. The owner decides which choices have that standing. When the owner sets out to make a decision record, an agent can draft it and record the outcome once agreed. Otherwise, keep planning choices, answers from discussion, and ticket-specific tradeoffs with the work. If a choice seems worth applying more broadly, ask the owner whether to adopt it and where it should apply.

File the record in the subject's `decisions/` folder as described in [Organization](organization.md). The short template covers the question, scope, options that mattered, choice, and reason. The fuller architectural decision record gives technical decisions room for constraints, tradeoffs, consequences, and ways to check the result. Both draw on [Markdown Architectural Decision Records](https://adr.github.io/madr/).

Use the following values for `decision_status`.

| Value | When to use it |
| --- | --- |
| `proposed` | The owner is considering the proposal. The question is still open. |
| `accepted` | The owner adopted the ruling for its stated scope. |
| `rejected` | The owner considered the proposal and declined it. Keep what was proposed and why the owner passed on it. |
| `deprecated` | The owner retired an accepted decision without replacing it. It can be enough to say the rule no longer serves a purpose. Keep the record so readers can see why it once applied. |
| `superseded` | A newer ruling replaces the old one. Link the two records in both directions. |

Record who decided and when, if known. Keep the original scope and reasoning when a ruling is retired. Link supporting notes and mention any change in circumstances that would make the choice worth revisiting. Alternatives considered within a decision can stay in that record. A proposal warrants its own rejected record when the owner wants future readers to know why it was declined.

## What to keep

Ask "What would someone have to rediscover or ask again if we left this out?" Keep important discoveries, open questions and their eventual answers, and the reasons behind choices made or deferred. A hard-to-find code path or a session-specific constraint can help the next agent resume. Omit routine file lists and details that are quicker to look up. A session can end with no useful addition. Vaults and subjects can refine this judgment in their guidelines.

During authorized edits, cut disproven assumptions and incidental detail from working notes as the investigation moves on. If ruling out a cause explains the eventual choice, keep that reason in a sentence. If an earlier decision relied on a mistaken belief, correct the claim and preserve what the decision-maker knew at the time. When condensing personal observations, keep details that explain the owner's experience, such as the same frustration recurring months apart.

Age and frequency of use alone are poor reasons to discard a note. An old ticket can answer a question on a different project. A vault with recoverable history, such as Git, may allow broader pruning in its local guidelines.
