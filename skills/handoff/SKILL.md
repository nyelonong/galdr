---
name: handoff
description: Use when the user runs /galdr:handoff to pass work to a fresh session, a worker or reviewer session, or tomorrow's session.
disable-model-invocation: true
---

# handoff

Writes a brief that a fresh session can act on with no other context, and reads back
its report.

## Write the brief

Path: `docs/plans/<YYYY-MM-DD>-<topic>-brief-<n>.md`, `n` counting from 1. Sections, in
order:

1. **Goal**: one paragraph, the outcome, not the steps.
2. **Approved scope**: what may change, and what must not.
3. **Read first**: paths to the plan, spec and code, never copies of them.
4. **State**: each claim with the command that proved it this session; any claim not
   checked this session starts with `UNVERIFIED:`.
5. **Checks**: the exact commands that decide done.
6. **Stop when**: done, blocked on a user decision, or a check fails three times.
7. **Report to**: `docs/plans/<YYYY-MM-DD>-<topic>-report-<n>.md`, holding status
   (`complete`, `blocked`, `needs-decision`, `failed`), a diff summary, evidence lines,
   and open questions.

Done when a reader with only this file and the repo could start work. Give the user
the command to open the fresh session on it.

## Read the report

1. Treat the report as claims: read the diff and rerun its checks.
2. Accepted: update the plan file's checkboxes, evidence and `next:`.
3. Not accepted: append a `## Review fixes` section to the same brief, one line per
   fix, each with its check, and hand it back.

## Resuming later

A new session reads the newest brief or the plan file's `next:`, runs the checks to
confirm the claimed state, and acts on what the commands show, not on the prose.
