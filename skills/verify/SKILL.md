---
name: verify
description: Use before claiming any task, gate, or bugfix is done — proves the claim with a command run this message instead of trusting memory or a report. Invoke via route or explicit command.
---

# Verify

A completion claim is only as good as the command that proves it, run in this
message. A claim backed by an older run, a subagent's word, or a green-looking suite
with hidden skips is not verified — it is an assertion.

## Do not

- Claim a task, gate, or bugfix is done without running the proving command yourself,
  in this message.
- Accept a subagent's report as evidence. Read its diff, then run the gate yourself.
- Count a run with skipped tests as a pass without naming the skip count and the
  reason for the skip.
- Skip the red-green revert proof when claiming a bug is fixed.
- Reuse a command's output from earlier in the conversation once the code under test
  has changed since that run.

## Claim → evidence table

Every completion claim gets one row: the claim, the command that proves it, the
freshness rule.

| Claim | Command that proves it | Freshness |
|---|---|---|
| "Tests pass" | the repo's test command (below) | run this message; a run before the last code edit is stale |
| "Typecheck is clean" | the repo's typecheck command | same rule |
| "The bug is fixed" | red-green revert proof | same rule |
| "The gate passed" | full gate manifest | same rule |

Freshness rule, stated once: if the last command run against the current code was
before this message, run it again before claiming anything. Stale evidence is not
evidence.

## Skip-count rule

Every test-run claim reports the skip count: "N passed, M skipped." A suite that
silently skips its integration tests (for example, docker-gated tests with docker
down) did not run those tests — say so, and name the dependency that caused the skip
(e.g., "37 skipped: docker not running"). Never count a run with unexplained skips as
a pass; a silent skip means the gate did not run.

## Red-green revert proof (bugfixes)

A bugfix claim needs three steps, not one passing test:

1. Revert the fix, keep the test. Run the test — it must fail.
2. Restore the fix. Run the test — it must pass.
3. Report both results. A test that only ever ran with the fix in place has not shown
   that the fix caused anything.

## Subagent-report-is-never-evidence

A subagent's "done" or "tests pass" is a claim, not evidence — the same freshness and
trust rules that apply to your own memory apply to another agent's report. Before
accepting it: read the diff, then run the gate command yourself. Only your own fresh
run counts.

## Proportionality

- In-task (one step inside a wave): typecheck + the focused tests for the changed
  area.
- Wave gate: the full gate manifest.
- Branch finish: the full gate manifest + invariant checks + e2e where configured.

## Antigravity: browser verification

On Antigravity (no terminal gate command), the fresh-evidence check is browser
verification: capture screenshots and a recording of the running app, in this
message, against the current code. Two rules bind this mode:

1. The EV line is still written to memory-progress.md (below) — browser evidence is
   evidence, not a substitute for the ledger.
2. The hard gate is not skipped by an "Always Proceed" policy. If the app cannot be
   launched or the screenshots cannot be produced, the gate fails; it does not
   silently pass.

## Gate commands

Read the gate manifest from the repo's `docs/agents/galdr.md` (written by `setup`).
When that file does not exist yet, use these literal fallbacks:

- Go repo: `gofmt -l .`, `go vet ./...`, `go test ./...`
- TS repo: `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm test`

## EV line

Every gate run writes one line to memory-progress.md:

```
EV [<scope>] <command> → <verdict> <key numbers> @<sha>
```

Example:

```
EV [w2/gate] go test ./... → PASS 412 passed 0 skipped 14.2s @d4e5f6a
```

## When you catch yourself thinking

| Thought | Reality |
|---|---|
| "I'll verify at the end" | Stale evidence is not evidence; verify now |
| "The subagent's report says it passed" | Reports are claims; run the gate yourself |
| "The suite is green" | Check the skip count; skipped is not passed |
