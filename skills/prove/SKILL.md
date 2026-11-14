---
name: prove
description: Use before you change production code, before you claim that work is complete, or when you audit a document against code.
---

# prove

Every change gets a proof: a test or a check that can fail. This skill tells you how to
write the proof and when a claim of "done" is true.

## 1. Bugs, regressions and test-first requests

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

This rule applies to a bug fix, a regression, and a change that the user asks to be
test-first. If no failing test exists, stop. Write the test first.

1. Write one test for the next small behavior.
2. Run the test and read the failure.
   - The assertion fails for the expected reason: continue.
   - The test does not compile, or it crashes: fix the test.
   - The test passes: it proves nothing. Write it again.
3. Record `EV [<task> RED] <command> → FAIL (<reason>)`.
4. Write the smallest code that makes the test pass. Record
   `EV [<task> GREEN] <command> → PASS`.

If you wrote code for a bug before its test, delete the code. Do not keep it as a
reference. Start again from a failing test.

## 2. New behavior

1. Name the proof before you write code. The `Proof:` line of the task names the tests
   and the boundary that they use.
2. Write the tests from the requirement, not from the code. Write them before the code
   or with it, at a public boundary.
3. Show that each new test can fail. Break the behavior once, run the test, and record
   the failure as an `EV` line.

## 3. Test kinds

- Unit tests run in one process. They use no network, real clock, sleep, Docker,
  credentials or database.
- Integration tests use an isolated test instance of the database, queue or HTTP
  service. Their set-up and clean-up give the same result each time. Keep them apart
  from unit tests.
- Contract tests use an approved sandbox or test account. Before you build a simulator
  of an upstream service, ask if a sandbox or a test key exists.
- Smoke tests and end-to-end tests stay local. Do not commit them.
- Never point a test at a live endpoint or at production credentials.
- Test the behavior that a caller can see. Do not test configuration values or private
  internals.
- Use a mock only at a boundary that you can name, with the reason that the real
  dependency cannot run there. Prefer the real dependency or an in-memory fake.

## 4. Claim "done" only with fresh evidence

NO COMPLETION CLAIMS WITHOUT FRESH EVIDENCE.

- Run the proving command yourself after the last related edit. Do not use an older run.
- A subagent report is a claim. Read its diff and run the checks yourself.
- Each test claim states "N passed, M skipped" and the cause of each skip, for example
  "37 skipped: docker not running".
- "Fixed" needs a revert proof. Revert the fix and keep the test. Watch the test fail.
  Put the fix back. Watch the test pass. Report the two runs.
- Use an earlier result only if no related edit came after it. Run again only the checks
  that are old or missing.
- A test that passes and fails without a code change is a finding. Run again only the
  smallest set of tests that shows it. Stop when the result is clear. Report it. If it
  blocks the proof of this change, it is P1: fix it here. If not, it is P2.

The evidence ladder is: said, cited (`path:line`), reasoned, ran, reproduced. "Done"
needs **ran**. "Fixed" needs **reproduced**. Name the rung when a claim is below ran.

## 5. Which checks to run

Find the checks that the repository enforces, in this order:

1. The CI configuration, for example `.github/workflows`.
2. The `Makefile` targets and the package scripts.
3. The `CLAUDE.md` or `AGENTS.md` of the repository.

If the repository defines no checks, read `references/checks.md` and use the defaults
for the language. At each closeout, run the checks for the changed packages. At the
finish, run the full set. Report each check that you did not run, with the reason, for
example "golangci-lint: no config".

Record each run in the Progress section of the plan:
`EV [<scope>] <command> → <verdict> <counts> @<sha>`.

## 6. Every change

- When the tests are green, clean up names, duplicates and comments. A new comment
  stays only if the comments keep list of review allows it.
- While you work, run the focused test and the type checker.
- Commit the test and the code together, at the closeout of their logical unit. Do not
  commit in the middle of a unit.
- If the user asked for browser approval, keep the change uncommitted until the gate
  approves it.

## 7. Document audit

Use `references/doc-audit.md` to check a design, architecture or runbook document
against the code. Also use it to write a new document that explains a subsystem with
citations.

## Rationalizations

| Thought | Reality |
|---|---|
| "Too simple to test" | Simple things break. The test is fast, so write it. |
| "I'll check at the end" | Old evidence is not evidence. Check now. |
| "The subagent's report says it passed" | A report is a claim. Run the checks yourself. |
| "The suite is green" | Read the skip count. A skipped test did not pass. |
| "The fix is obvious, skip root cause" | Symptom fixes come back. Find the cause. |
| "The test is hard to write" | A hard test is design feedback. Look at the boundary. |
