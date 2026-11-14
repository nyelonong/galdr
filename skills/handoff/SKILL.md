---
name: handoff
description: Use when the user runs /galdr:handoff to pass work to a new session, a worker or reviewer session, or the session of the next day.
disable-model-invocation: true
---

# handoff

handoff writes a brief that a new session can use with no other context. Then it reads
the report that comes back.

## Write the brief

Use the path `docs/plans/<YYYY-MM-DD>-<topic>-brief-<n>.md`. Count `n` from 1. Write
these sections in this order:

1. **Goal**: one paragraph about the outcome, not the steps.
2. **Approved scope**: what can change, and what must not change.
3. **Read first**: paths to the plan file and the code, not copies.
4. **State**: each claim with the command that proved it in this session. A claim that
   you did not check in this session starts with `UNVERIFIED:`.
5. **Checks**: the exact commands that decide if the work is complete.
6. **Stop when**: the work is complete, a user decision blocks it, or a check fails
   three times.
7. **Report to**: `docs/plans/<YYYY-MM-DD>-<topic>-report-<n>.md`. The report holds the
   status (`complete`, `blocked`, `needs-decision`, `failed`), a diff summary, evidence
   lines and open questions.

The brief is complete when a reader with only this file and the repository can start
work. Give the user the command that opens the new session on it.

## Read the report

1. The report is a set of claims. Read the diff and run its checks again.
2. If you accept the work, update the checkboxes, Progress and the status line of the
   plan.
3. If you do not accept it, add a `## Review fixes` section to the same brief. Write one
   line for each fix, with its check. Then give the brief back.

## Continue later

A later session starts from the newest brief. It reads the state and runs the checks
again first, and it obeys the resume rules of galdr §3.
