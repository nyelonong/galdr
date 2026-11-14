# Plan format

One file per piece of work, `docs/plans/<YYYY-MM-DD>-<topic>.md`. `shape` writes the
top half (title to Decisions); playbooks add the rest. Leave out a section that
would be empty, except Done when, Tasks and Progress.

```markdown
# <Title: the outcome, in plain words>

Status: <draft | approved <date> | building | released <date>> · <where: branch, commit, PR, live> · next: <one action>

Repo: <repo>. Parent: <plan path, if any>. Replaces: <task or plan, if any>.

## Goal
One paragraph: what changes for whom, and why.

## Out of scope
- <what is deliberately not done>

## Done when
- <each decidable by a command or an observable check>

## Design
<diagram when three or more parts talk to each other>

| Piece | What it does |
|---|---|
| `<path>` | <one line; contracts, storage, limits and safety go here or below> |

## Decisions
| # | Decision | Choice | Why / trade-off | Source |
|---|---|---|---|---|
| 1 | <question> | <choice> | <why, and what it costs> | asked · found (`path:line`) · assumed · <owner> to decide |

## Before building
| Check | Finding | Effect |
|---|---|---|

## Releases
| Release | Covers | Depends on |
|---|---|---|

## Tasks
- [ ] <task> · Proof: `<command>`
- [ ] You: <step only the user can do>

## Review
<independent review needed or not, and why; who opens PRs>

## Progress
- <date>: <what happened; a decision that changed names the section it supersedes>
- EV [<scope>] <command> → <verdict> <counts> @<sha>
```

Every check run is an `EV` line in Progress, with skip counts.
