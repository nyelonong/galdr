---
name: review
description: Use when reviewing a branch, wave, or PR's changes against a SHA range — checks the diff against this repo's conventions and against the originating plan/spec, as two separate axes that are never merged into one verdict. Invoke via route or explicit command.
---

# review

Two-axis review of a SHA range: **Standards** (does the diff follow this repo's
conventions) and **Spec** (does the diff match what the plan/spec asked for). The two
axes run separately and are never merged or cross-ranked — each ends in its own
verdict.

## Pin the range and the sources

- SHA range: `base...head` (three-dot, against the merge-base). Confirm both ends
  resolve and the diff is non-empty before dispatching anything — a bad ref or empty
  diff fails here, not inside two parallel subagents.
- Spec source: the plan/spec the branch or wave was built from. If none exists, say so
  and skip the Spec axis's per-requirement findings (Standards still runs).
- Standards sources: this repo's gate manifest (`docs/agents/galdr.md`; the verify
  skill's fallback list if that file doesn't exist yet), any configured Standards-axis
  sources (for example DESIGN.md, a panel-island rule, a mirror-pair invariant), and
  the smell list below.

If the host environment already exposes a two-axis review mechanism (a `/code-review`
command), it may be used to run the dispatch — the sourcing, verification, severity
gate, and separate-axes rules below still apply to whatever it returns.

## Two clean-room subagents, dispatched together

Send one message with two `Agent` dispatches, both general-purpose, both clean-room:
each gets only what's pasted into its own prompt, nothing from the other axis and
nothing from this session's history. Paste source content inline; never point a
subagent at a path and ask it to read and obey skill content — that's path-based rule
injection, and it invalidates the run.

**Standards subagent** gets: the diff, the commit list, the gate manifest commands (run
them, report failures), the configured Standards-axis sources, and the smell list. It
also runs the **correctness pass**: for each changed test, check that it actually
exercises the behavior it claims — not asserting a mock, not asserting the
implementation's own internals, not a snapshot with no stated intent. A passing suite
built on tautological tests is a Standards finding, not a clean pass.

**Spec subagent** gets: the diff, the commit list, and the plan/spec content. It
reports three things only: requirements **missing** or partial, behavior in the diff
the plan didn't ask for (**creep**), and requirements that look done but whose
implementation is **wrong**. Every finding quotes the plan line it's checked against.

## Verify every finding before it's reported

A finding is not reported until it has been reproduced or refuted:

- Reproduce: run the failing case, read the exact lines, show the break.
- Refute: show why the apparent problem doesn't hold — tooling already covers it, the
  repo's own standard endorses it, or the finding misreads the plan line.

Report only what survives this check.

## Report findings

Where the host provides a `ReportFindings` tool, route every surviving finding through
it, one entry per finding, each carrying a verdict of `CONFIRMED` (reproduced) or
`PLAUSIBLE` (likely but not fully reproducible — say what's missing to confirm it).
Where the host has no such tool, report the same information as a markdown table:

| Axis | Severity | Verdict | File:line | Finding | Cited standard / plan line |
|---|---|---|---|---|---|

## Severity gate, within each axis

- **Critical** — fix before the merge-request.
- **Important** — fix before the next wave.
- **Minor** — note; no forced action.

The gate applies inside each axis on its own. A Critical on one axis does not promote
or demote anything on the other. A finding deferred rather than fixed now gets a
backlog entry per /galdr:backlog (skills/backlog/SKILL.md) — don't restate the format
here.

## Axes stay separate

Report Standards and Spec under their own headings, each with its own forced verdict —
one of `PASS`, `PASS WITH NOTES`, or `FAIL` — plus that axis's worst open finding.
Never combine them into one verdict, one ranking, or one severity count. A change can
fail one axis and pass the other; that's a real outcome to report, not something to
reconcile into a single number. If asked "so what's the verdict," give both axes'
verdicts, not an average or a pick-one-winner answer.

## Receiving findings

- Verify a finding before implementing its fix. A finding is a claim, not an order —
  check it against the codebase before touching production code.
- When findings conflict, this precedence decides: the user's word outranks this review's
  own subagent findings, which outrank an external reviewer or tool's findings.

## The plan can be the bug

A Spec-axis finding sometimes traces back to a wrong plan line, not wrong code. When
that's the root cause, say so and route back to the plan — don't patch code to satisfy
a plan line that is itself the error.

## Go/TS smell list (Standards axis, 11 items)

Fowler smells kept for this stack. A documented repo standard always overrides one of
these; each is a judgement call, not a hard violation; skip anything a linter already
enforces.

- **Mysterious Name** — a name doesn't reveal what it does or holds → rename it.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file →
  extract the shared shape, call it from both.
- **Feature Envy** — a function reaches into another type's data more than its own →
  move it onto the data it envies.
- **Data Clumps** — the same fields or params keep travelling together → bundle them
  into one type.
- **Primitive Obsession** — a primitive or string stands in for a domain concept →
  give the concept its own type.
- **Repeated Switches** — the same switch/if-cascade on one type recurs in the diff →
  replace with one shared dispatch point.
- **Shotgun Surgery** — one logical change forces edits scattered across many files →
  gather what changes together into one place.
- **Divergent Change** — one file or module changes for several unrelated reasons →
  split it so each changes for one reason.
- **Speculative Generality** — abstraction or hooks added for a need the spec doesn't
  have → delete it.
- **Message Chains** — a call walks object→object→object to reach what it needs → hide
  the delegate behind one method on the first object.
- **Middle Man** — a type or function that mostly delegates onward → cut it, call the
  real target direct.

Dropped from the Fowler baseline for this stack: Refused Bequest — Go has no class
inheritance to refuse. A repo's own configured Standards source may still flag it.

## Output shape (what branches/finish consumes)

```
## Standards
<findings — ReportFindings or table>
Verdict: PASS | PASS WITH NOTES | FAIL — worst: <finding or "none">

## Spec
<findings — ReportFindings or table>
Verdict: PASS | PASS WITH NOTES | FAIL — worst: <finding or "none">
```

No combined verdict line follows either heading. Downstream consumers read the two
verdicts separately.
