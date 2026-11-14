---
name: tdd
description: Use before writing or changing any production code, including features, bug fixes and refactors.
---

# TDD

Every change ships with a test that proves it. The loop depends on the change.

## Bugs, regressions, and test-first on request

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

A hard rule for bug fixes, regressions, and test-first requests: with no failing test
yet, stop and write one.

1. Write one failing test for the next smallest behavior.
2. Run it and read the failure: an assertion failing for the expected reason means
   continue; a compile error or crash means fix the test; a pass means the test proves
   nothing, so rewrite it.
3. Record `EV [<task> RED] <test cmd> → FAIL (<expected failure>)`.
4. Write the least production code that passes it, then record `EV [<task> GREEN]
   <test cmd> → PASS`.

Code written for a bug before its test is deleted, not kept as reference, and the loop
restarts from a failing test.

## New behavior

1. Name the proof before coding: the task's `Proof:` line says which tests, at which
   boundary, decide it.
2. Write those tests from the requirement, never from the code: before or alongside the
   code, at a public boundary.
3. Show each new test can fail: run it once with the behavior removed or broken and
   record the failure as an `EV` line.

## Every change

- Clean up with the tests green: names, duplication, and comments. A new comment stays
  only if it is on review's comments keep list.
- Commit the test and the code together, one logical change; when the user asked for
  browser approval, leave it uncommitted until the gate approves.
- Run the focused test and type checker while working, the full suite before any
  completion claim.

## Test isolation

- Unit tests run in one process: no network, real clock or sleep, Docker, credentials,
  or databases.
- Behavior that needs a database, queue or HTTP transport gets an integration test
  against an isolated test instance, with repeatable set-up and clean-up, apart from
  the unit tests.
- Never point a test at a live endpoint or production credentials.
- Test observable behavior, not configuration values or private internals.

## Mock gate

Mock only at a boundary you can name, with the reason the real dependency cannot run
there. Prefer the real dependency or an in-memory fake. A test that only checks a mock
was called, restates the implementation, or snapshots output with no stated intent
proves nothing.

## Rationalizations

| Thought | Reality |
|---|---|
| "Too simple to test" | Simple things break; the test is fast — write it |
| "I'll verify at the end" | Stale evidence is not evidence; verify now |
| "The fix is obvious, skip root cause" | Symptom fixes recur; find the cause |
| "The test is hard to write" | Hard test = design feedback; check the boundary |
