---
name: verify
description: Use before claiming any task, check, or bug fix is done, or when auditing a document's claims against the code.
---

# Verify

NO COMPLETION CLAIMS WITHOUT FRESH EVIDENCE.

A completion claim is only as good as the command that proves it. A claim backed by an
older run, a subagent's word, or a green-looking suite with hidden skips is an
assertion, not evidence.

## Do not

- Claim a task, check, or fix is done without running the proving command yourself,
  after the last relevant edit.
- Accept a subagent's report as evidence. Read its diff, then run the checks yourself.
- Count a run with skipped tests as a pass without naming the skip count and why.
- Claim a bug is fixed without the revert proof below.

## Evidence ladder

Every claim sits on one rung; name it when the rung is below **ran**:

1. **said**: someone stated it.
2. **cited**: a `path:line` or link shows it.
3. **reasoned**: it follows from cited facts.
4. **ran**: a command run after the last relevant edit shows it.
5. **reproduced**: it failed without the change and passed with it.

"Done" needs **ran**. "Fixed" needs **reproduced**: revert the fix and keep the test,
watch it fail, restore the fix, watch it pass, report both.

## Reuse and freshness

Reuse a result only when it was produced after the last edit that could affect it.
Rerun what is stale or missing, not everything. Any code change after a review approval
voids that approval. Every test claim states "N passed, M skipped", and names what
caused any skip ("37 skipped: docker not running"); a silent skip means the check did
not run.

## Look beyond the diff

For a change that touches data, migrations, concurrency, security, external systems or
a public contract, inspect what the diff does not show: callers, contracts, persisted
and wire formats, downstream readers, lifecycle timing, feature flags, and external
dependencies. List every fact you could not prove as an explicit risk.

## Checks and records

Take the check commands from the repo's `CLAUDE.md` or `AGENTS.md`; otherwise use the
language's format, lint, type-check and test commands. Record each run in the plan's Progress:

```
EV [<scope>] <command> → <verdict> <key numbers> @<sha>
```

## Document audit

When the request is to check a design, architecture or runbook document against the
code, or to explain a subsystem as a new cited document, read
`references/doc-audit.md` and follow it.

## When you catch yourself thinking

| Thought | Reality |
|---|---|
| "I'll verify at the end" | Stale evidence is not evidence; verify now |
| "The subagent's report says it passed" | Reports are claims; run the gate yourself |
| "The suite is green" | Check the skip count; skipped is not passed |
