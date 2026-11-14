# Plan format

Each piece of work has one file, `docs/plans/<YYYY-MM-DD>-<topic>.md`. The file stays
local and uncommitted, unless the repository commits its plans. `shape` writes the top
half, from the title to Decisions. Playbooks add the rest. Leave out a section that has
no content. Always keep Done when, Tasks and Progress.

```markdown
# <Title: the outcome, in plain words>

Status: <draft | approved <date> | building | released <date>> · <where: branch, commit, PR, live> · next: <one action>

Repo: <repo>. Parent: <plan path, if any>. Replaces: <task or plan, if any>.

## Goal
One paragraph: what changes for whom, and why.

## Out of scope
- <work that this plan does not do>

## Done when
- <each item decidable by a command or an observable check>

## Design
<one diagram for each material decision>

| Piece | What it does |
|---|---|
| `<path>` | <one line: contracts, storage, limits and safety go here or below> |

## Decisions
| # | Decision | Choice | Why / trade-off | Source |
|---|---|---|---|---|
| 1 | <question> | <choice> | <why, and the cost> | asked · found (`path:line`) · assumed · <owner> to decide |

Risks: <changed contracts, permissions, sensitive data, lifecycle, migration or recovery>

## Before building
| Check | Finding | Effect |
|---|---|---|

## Releases
| Release | Covers | Depends on |
|---|---|---|

## Tasks
- [ ] <task> · Proof: `<command>`
- [ ] You: <step that only the user can do>

## Review
<independent review necessary or not, and the reason. The person who opens PRs.>

## Progress
- <date>: <event. A changed decision names the section that it replaces.>
- EV [<scope>] <command> → <verdict> <counts> @<sha>
```

Select each diagram for its purpose:

- **Architecture**: components and boundaries.
- **Sequence**: ordered interactions, with the important failure paths.
- **Swimlanes**: ownership and handoffs.
- **ERD**: changed entities, keys and cardinality.

Do not show the same flow in two diagrams, or in a diagram and in prose. Write each check
run as an `EV` line in Progress, with its skip count.
