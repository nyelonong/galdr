---
name: debug
description: Use when diagnosing a bug, flaky test, unexpected behavior, or production incident, before proposing or writing any fix. Invoke via route or explicit command.
---

# Debug

NO FIXES WITHOUT ROOT CAUSE.

This is a hard rule, not a preference. A fix without a root cause is a guess that
happened to change the symptom. If you are about to change code to make a bug go away
and you cannot state the root cause it addresses, stop.

## Do not

- Change code as a fix before a repro exists that reproduces the bug on demand.
- Claim any behavior — what happens, when, how often — without pasting the exact
  command and its output that showed it, in the message making the claim.
- Try a fourth variant of a fix at a site that has already failed three times; escalate
  instead.
- Close a production incident without leaving a root-cause WIP line with a named
  owner. Mitigation is never the end state.

## Feedback loop first

Before theorizing, build a repro: a command whose output differs depending on which
hypothesis is true. Run it before proposing a fix. A hypothesis picked without a
command that can distinguish it from the alternatives is a guess, not a diagnosis.

## Pasted-command evidence gate

Any claim about behavior needs the exact command and its output pasted in the message
that makes the claim. "seems to happen when..." without a paste is speculation. This
applies to your own claims and to a subagent's report about the bug — re-run it
yourself before repeating its conclusion.

## HYP ledger

Every hypothesis gets one line in memory-progress.md, written as it is formed, not
after it resolves:

```
HYP <n>: <hypothesis> → <experiment> → <result>
```

Example:

```
HYP 3: server closes idle SSE conns after 55s → curl -N, hold idle 70s, grep server
log for FIN → confirmed, server-side timeout fires at 55s
```

End every debugging session with the current hypothesis state written this way, even
when unresolved — "no narrowed hypothesis yet" is a valid result; a missing line is not.

## Repro menu

Ten ways to build a repro. Pick the cheapest one that distinguishes your hypotheses;
do not reach for the heaviest by default.

1. A failing test that reproduces the bug
2. `curl` against the endpoint
3. A throwaway `tsx`/`go run` script
4. Grep across existing logs
5. Bisect (`git bisect` or manual halving) to the introducing commit
6. A minimal fixture that isolates the input
7. Docker service isolation — run the one dependency alone
8. Race detector (`-race`, or the equivalent for the language)
9. A Playwright trace, for browser flows
10. An SSE/WebSocket client dump, for streaming bugs

## Debug tags

Temporary instrumentation — a log line or print added only to test a hypothesis — is
tagged `DBG-<topic>` (for example `DBG-sse-drop`), so it is greppable. Before any
commit: `grep -rn "DBG-" <path>` and remove every hit, or confirm the search returns
none. A `DBG-` tag left in a commit is unfinished cleanup, not something to skip.

## Correct seam

Instrument at the boundary whose two sides you're trying to distinguish, not upstream
or downstream of it. If the hypothesis is "the client drops the connection vs. the
server closes it," the seam is the socket between them — instrumenting only the client
cannot tell you which side initiated the close.

## Phase-1 time-box

Thirty minutes without a narrowed hypothesis: stop where you are. Write the HYP ledger
line for the state you have, then step back to an architecture read — re-read the
relevant design doc or code path from the top before running another instrumented
attempt. Continuing to poke at the same layer past thirty minutes without a hypothesis
is a sign you're missing structure, not a shortcut to one.

## Three-strikes rule

Three failed fixes at the same site (same function, same file, same layer) mean the
defect is upstream of that site. Stop patching there. Escalate to design/architecture
level — the real fix belongs somewhere else in the system, not in a fourth variant of
the same patch.

## Incident branch: stabilize first

A production incident (failures happening now, in prod) is diagnosed differently:
mitigate before you diagnose. Mitigation means whichever of these stops the failures
fastest — flag off, roll back, pause the queue. Root-cause work does not begin until
mitigation is in effect, and never replaces it. Once the incident is stable, root-cause
work becomes a WIP line with a named owner and a real next action — never waived, and
never silently dropped once traffic recovers:

```
**WIP** root-cause: <incident> — next: <exact investigation step>, owner: <name>
```

A leisurely investigation while failures continue is the wrong order, and so is closing
the incident once it's mitigated with no root-cause line at all.

## Routing

Check for the environment's language- or browser-specific debugging skills, when
installed, before improvising instrumentation — for example `golang-troubleshooting`
for Go runtime issues, a benchmarking skill for a performance question, or Playwright
tools for a browser flow. Use them when they exist; this skill's loop still applies
underneath — repro first, evidence gate, HYP ledger.

## Rationalizations

| Thought | Reality |
|---|---|
| "The fix is obvious, skip root cause" | Symptom fixes recur; find the cause |
| "One more print will crack it" | No hypothesis, no instrument — write the HYP line first |
| "It's in prod, just ship the real fix now" | Mitigate first; root cause follows as a WIP line, never skipped |
| "I've patched this spot before, one more try" | Three strikes here means the defect is upstream — stop patching, escalate |
