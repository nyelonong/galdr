---
name: tdd
description: Use before writing or changing any production code, including features, bug fixes and refactors.
---

# TDD

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

This is a hard rule, not a preference. If you are about to write or edit production
code and no failing test exists for that change yet, stop and write the test first.

## The loop

1. Write one failing test for the next smallest behavior.
2. Run it and read the failure:
   - **Fails as expected** (the assertion fails for the reason you expect): continue.
   - **Fails wrong** (compile error, crash before the assertion): fix the test or its
     setup; do not touch production code yet.
   - **Passes** with no production change: the test proves nothing; rewrite it so it
     fails first.
3. Record `EV [<task> RED] <test cmd> → FAIL (<expected failure>)`.
4. Write the least production code that passes it.
5. Run the test and the type checker to green; record `EV [<task> GREEN] <test cmd> →
   PASS`.
6. Clean up with the test still green: names, duplication, and comments. A new comment
   stays only if it is on review's comments keep list (license header, tool directive,
   non-obvious constraint or decision, API contract, issue link).
7. Commit the test and the code together: one logical change, conventional prefix. When
   the user asked for browser approval, leave it uncommitted until the gate approves.

In the loop, run only the focused test and the type checker. Run the full suite before
any completion claim.

## If code exists before its test

Delete it. Do not keep it as reference and do not wrap tests around it. Restart the
loop with a failing test.

## Test isolation

- Unit tests run in one process: no network, real clock or sleep, Docker, credentials,
  or databases.
- Behavior that needs a database, queue or HTTP transport gets an integration test
  against an isolated test instance, with set-up and clean-up that give the same
  result every run, kept apart from the unit tests.
- Never point a test at a live endpoint or production credentials.
- Test observable behavior, not configuration values or private internals.

## Mock gate

Mock only at a boundary you can name, with the reason the real dependency cannot run
there (network, clock, cost). Prefer the real dependency or an in-memory fake. A test
that only checks a mock was called, restates the implementation, or snapshots output
with no stated intent proves nothing.

## Rationalizations

| Thought | Reality |
|---|---|
| "Too simple to test" | Simple things break; the test is fast — write it |
| "I'll verify at the end" | Stale evidence is not evidence; verify now |
| "The fix is obvious, skip root cause" | Symptom fixes recur; find the cause |
| "The test is hard to write" | Hard test = design feedback; check the boundary |
