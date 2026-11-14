---
name: debug
description: Use when you diagnose a bug, a flaky test, unexpected behavior or a production incident, before you propose or write a fix.
---

# Debug

NO FIXES WITHOUT ROOT CAUSE.

This is a hard rule. A fix without a root cause is a guess that changed the symptom. If
you want to change code to remove a bug and you cannot state its root cause, stop.

## Do not

- Do not change code as a fix before a repro exists. A repro shows the bug on demand.
- Do not claim a behavior (what happens, when, how often) without the exact command and
  its output in the same message.
- Do not try a fourth fix at a site where three fixes failed. The defect is upstream.
  Go back to the design.
- Do not close a production incident without an open root-cause item. The item names an
  owner and a next step. Mitigation is never the end.

## Make a repro first

Before you make a theory, build a repro. A repro is a command whose output changes with
the hypothesis that is true. Use the cheapest one that separates the hypotheses, for
example a failing test, `curl`, a log search or `git bisect`. Run a subagent's claim
about the bug again before you repeat it.

## Hypotheses

Write each hypothesis when you make it, in the plan file or in the report:

```
HYP <n>: <hypothesis> → <experiment> → <result>
```

- Add instruments at the boundary between the two sides that you want to separate.
- Mark temporary logs with `DBG-<topic>`. Before each commit, run
  `grep -rn "DBG-" <path>` until it finds nothing.
- After thirty minutes without a narrower hypothesis, write down the current state.
  Then read the code path again from the top before the next attempt.
- At the end of each session, write the state of the hypotheses, even "no narrower
  hypothesis yet".

## Incident: stabilize first

When failures occur in production now, stop the failures before you diagnose. Use the
fastest method: turn a flag off, roll back, or pause the queue. Then open the root-cause
item with an owner and a specific next step.

## Rationalizations

| Thought | Reality |
|---|---|
| "The fix is obvious, skip root cause" | Symptom fixes come back. Find the cause. |
| "One more print will crack it" | No hypothesis, no instrument. Write the HYP line first. |
| "It's in prod, just ship the real fix now" | Stop the failures first. The root cause comes next, as an owned item. Never skip it. |
| "I've patched this spot before, one more try" | Three failed fixes here mean the defect is upstream. Stop the patches. Go up to the design. |
