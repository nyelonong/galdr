---
name: debug
description: Use when diagnosing a bug, flaky test, unexpected behavior, or production incident, before proposing or writing any fix.
---

# Debug

NO FIXES WITHOUT ROOT CAUSE.

This is a hard rule, not a preference. A fix without a root cause is a guess that
happened to change the symptom. If you are about to change code to make a bug go away
and you cannot state the root cause it addresses, stop.

## Do not

- Change code as a fix before a repro exists that reproduces the bug on demand.
- Claim any behavior (what happens, when, how often) without pasting the exact command
  and its output in the same message.
- Try a fourth fix at a site that has already failed three times; the defect is
  upstream, so step back to the design.
- Close a production incident without an open root-cause item that names an owner and
  a next step. Mitigation is never the end state.

## Feedback loop first

Before theorizing, build a repro: a command whose output differs depending on which
hypothesis is true; pick the cheapest that tells them apart (a failing test, `curl`, a
log grep, `git bisect`). A subagent's claim
about the bug is re-run before it is repeated.

## Hypotheses

Write each hypothesis down as it is formed, in the plan file or the report:

```
HYP <n>: <hypothesis> → <experiment> → <result>
```

Instrument at the boundary whose two sides you are trying to tell apart. Tag temporary
logging `DBG-<topic>`, and before any commit run `grep -rn "DBG-" <path>` until it
returns nothing. Thirty minutes without a narrowed hypothesis: write down the state you
have and re-read the code path from the top before another attempt. End every session
with the hypothesis state written, even "no narrowed hypothesis yet".

## Incident: stabilize first

When failures are happening in production now, mitigate before diagnosing: flag off,
roll back, or pause the queue, whichever stops the failures fastest. Then open the
root-cause item, with an owner and a concrete next step.

## Rationalizations

| Thought | Reality |
|---|---|
| "The fix is obvious, skip root cause" | Symptom fixes recur; find the cause |
| "One more print will crack it" | No hypothesis, no instrument — write the HYP line first |
| "It's in prod, just ship the real fix now" | Mitigate first; root cause follows as an owned item, never skipped |
| "I've patched this spot before, one more try" | Three strikes here means the defect is upstream — stop patching, escalate |
