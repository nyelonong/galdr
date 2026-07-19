# Agent brief: <task id> — <short title>

Base SHA: `<sha>` · mechanical: <true|false>

## Behavioral contract

<One paragraph: what observably changes when this task is done — the outcome, not the
implementation steps.>

## Acceptance criteria (each box checkable by a command, not by reading and judging)

- [ ] <criterion 1 — name the command that verifies it>
- [ ] <criterion 2 — name the command that verifies it>
- [ ] <criterion 3 — name the command that verifies it>

## Seams and test list

Declared seams (from the plan): <seam 1>, <seam 2>

Test list, RED first, one entry per seam or behavior:
1. <test name> — <what it proves>
2. <test name> — <what it proves>

Evidence payload (from tdd): `EV [<task> RED] <test cmd> → FAIL (<expected failure>)`,
then `EV [<task> GREEN] <test cmd> → PASS`. Both lines required per test.

## Write-scope

Exact paths this task may create or edit:
- <path>
- <path>

Nothing outside this list. If the work needs a file not listed here, stop and return
`needs-decision` — do not add scope on your own judgment.

## Out of scope

- <path or behavior explicitly not touched, 1>
- <path or behavior explicitly not touched, 2>
- <path or behavior explicitly not touched, 3>

## Commit rules

- Atomic: one green pair per commit (failing test + the code that passes it), never
  split, never bundled with a second pair.
- Conventional prefix (`feat`/`fix`/`refactor`/`test`/`docs`/`chore`) matching the change.
- Commit only inside the write-scope above. No exceptions.
- `wip:` commits are reserved for session parking, not for task work.

## Return contract

Report exactly one status: `complete` / `blocked` / `needs-decision` / `failed`.

Every status includes: RED and GREEN EV lines for every test above, the commit list
(SHA + one-line message), and files touched (must match write-scope exactly).

`blocked` / `needs-decision` also carry the escalation payload: what was tried, what's
needed, one recommendation.

## The brief is the whole contract

No scope additions on your own initiative, even a small one. If the task needs
something this brief doesn't cover, stop and return `needs-decision` instead of
guessing.
