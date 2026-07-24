---
name: waves
description: Use when a plan already exists and is ready to run — dispatches each wave's tasks, reviews every return before trusting it, and gates advancement on evidence. Invoke via route or explicit command.
---

# waves

waves executes the task list a plan produced: wave by wave, dispatching each wave's
frontier, distrusting every report until it's checked, and gating the next wave on
evidence instead of a claim.

## Runtimes and dispatch

waves runs on three runtimes. Each names one dispatch mechanism, one progress view, and
one usage reader; the detail table is in `references/runtime-dispatch.md`.

- **Claude** — Workflow or Agent tool for dispatch; TodoWrite for the progress tree; the
  statusline rate-limit cache as the usage reader.
- **Codex** — subagents for dispatch (the AGENT-BRIEF is the dispatch prompt: spawn one
  agent per brief, wait for all, return a summary; `/agent` to inspect); task view for
  the progress tree; usage reader N/A.
- **Antigravity** — `start_subagent` for dispatch (dynamic subagents, isolated context,
  parallel); agent view for the progress tree; usage reader N/A.

Antigravity returns surface as native reviewable code diffs — detail in
`references/runtime-dispatch.md`. Two binding rules stay: the ledger is still written
(a diff is not evidence), and the hard gate is not skipped by an "Always Proceed" policy.

## Dispatch procedure

For each task in the wave's frontier:

1. Write the brief from `references/agent-brief-template.md`, filled in for this task:
   base SHA, write-scope, acceptance criteria, seams, and test list, taken from the plan.
   Write the filled brief to `<repo>/docs/briefs/<task-id>-brief.md`. Briefs are
   gitignored by default — the plan is the durable source and the brief is derived from
   it; a repo's config may flip this to committed via a `## Briefs` line in
   `docs/agents/galdr.md`. Writing brief files happens before dispatch, so it precedes
   the in-flight window; once any dispatch is out, the git-discipline rule below applies
   as written.
2. Before dispatching, append a WIP dispatch line to memory-progress.md (continue skill
   format): `**WIP** dispatched <brief path> @<base sha> scope=<paths> tier=<tier>
   model=<id> effort=<level|inherit|n/a> — next: review on return`. Effective values:
   `inherit` = mechanism supports effort but binding sets none; `n/a` = accepts none.
3. Dispatch with the declared write-scope as the only paths the subagent may touch.
4. On return, run the two-verdict review below before acting on anything the report
   claims.
5. After the review (or the mechanical diff sanity check), and before the next dispatch
   goes out, append the closure line to memory-progress.md: `EV [waves] <task-id>
   return reviewed status=<status> @<sha>` — `<task-id>` is the id from the brief
   filename recorded in the dispatch WIP line; `@<sha>` is the reviewed head commit at
   closure time, never the dispatch's base sha.

## Two-verdict review — distrust the report

A subagent's report is a claim, not evidence. Do not act on it as-is.

- Do not accept "tests pass," "all done," or an equivalent report without reading the
  diff yourself.
- Do not run code-quality review before spec compliance — order matters, and skipping
  the first step to get to the second hides missing scope.
- Do not skip running the gate commands yourself because the report says they were run.

Order, every time:

1. **Spec compliance first** — check the diff against the brief's acceptance criteria,
   checkbox by checkbox. Quote the criterion for every gap found.
2. **Code quality second** — only once spec compliance passes.

Severity: Critical findings are fixed now (before `complete`); Important before the
next task — mirroring review's branch-level severity gate.

## Status contract

Every dispatch returns exactly one of four statuses:

- `complete` — acceptance criteria met, gates green, commits made.
- `blocked` — cannot proceed on its own.
- `needs-decision` — a choice only the controller or user can make.
- `failed` — attempted and did not succeed.

`blocked` and `needs-decision` carry the ⚠️ escalation payload, all three parts, every
time:

1. What was tried.
2. What's needed to unblock or decide.
3. One recommendation — a single option with brief reasoning, not a menu.

## Model and effort tiers

- Task → tier: briefs marked `mechanical: true` → mechanical; implementation and per-task
  review → standard; planning, wave-gate review, and debug → top. A plan task's
  `**Model tier:** <tier> [@ <effort>]` line, when present, overrides this; omitted
  effort means the tier's binding.
- Tier → (model, effort): rows in `docs/agents/galdr.md` §Models (setup-written; row
  syntax and defaults named in setup, not here — models change, skill text shouldn't).
  No `@ <effort>` suffix means inherit — the session effort governs. Effort applies only
  where the mechanism accepts it (`references/runtime-dispatch.md`); elsewhere it's
  dropped — the ledger records `effort=n/a`.
- Ladder: `mechanical → standard → top → top@max` — one rung per escalation, whole binding
  taken. First failure: retry same binding; second: up one rung, retry once; third: stop
  the wave (STOP condition below). No-effort runtimes lack the `top@max` rung — a top-tier
  task's second failure stops the wave. `EV [waves] <task-id> attempt=<n> <tier>@<effort>
  → failed: <reason>`; `EV [waves] <task-id> attempt=2 escalate <old>@<eff> → <new>@<eff>`.
- Effort rejection: a config problem, not a task failure — re-dispatch the same
  model, no effort, same attempt. `EV [waves] <task-id> effort=<level> rejected →
  re-dispatched effort=n/a`.

## Proportional review

Review depth follows the brief's own classification, not a fixed ceremony:

- Brief marked `mechanical: true`: diff sanity check only — read the diff, confirm it
  does the small thing it claims, run the gates.
- Everything else: the full two-verdict review above.

## Wave gate

Before opening the next wave:

1. Run the verify skill against the full gate manifest — not the in-task tiered
   cadence, the full suite.
2. Run one refactor pass across the wave's tests. Refactoring belongs here, at the wave
   gate — the task's TDD loop stops at green.
3. Write the EV line for every gate command run, plus a wave-level status line, to
   memory-progress.md, **and** print the usage report (below) in your response to the
   user — the ledger line and the printed report are both required; neither substitutes
   for the other.

A wave gate that produced no EV lines has not happened, regardless of what the dispatch
reports said. Defer a task to a later cycle? Append it to the backlog per /galdr:backlog
(skills/backlog/SKILL.md).

## Live progress table

The plan's `## Progress` table (format in `skills/plan/SKILL.md`) is a derived view
waves maintains — never hand-edited; `memory-progress.md` stays the durable state:

- **Wave open** — mark the wave's frontier tasks `in-progress`.
- **Wave gate** — regenerate the whole table from `memory-progress.md`.
- **First dispatch of the run** — advance the spec's `Lifecycle status:` line to
  `in-progress`.

Both table writes happen only at points the controller may already write the repo (wave
open, wave gate) — never while a dispatch is in flight.

### Native progress tree

Alongside the plan table, waves keeps a native progress list mirroring the plan's tasks
(per-runtime mechanism in `references/runtime-dispatch.md`). Seed one `pending` entry
per task at run start; flip a wave's frontier tasks to `in_progress` at wave open; set
each to its final status at the wave gate. The native tree is an ephemeral mirror —
`memory-progress.md` stays the only durable state.

## Usage and token report

At each wave gate and at run end, waves **prints this report in its response to the
user** — a memory-progress.md EV line records the same numbers for the ledger but does
not, on its own, satisfy this; the user sees the block itself, every time, not a
summary folded into other text. Reports together:

- **Tokens** — spent this wave plus running cumulative, summed from each dispatch
  return's usage in the wave.
- **Usage limits (Claude only)** — the real 5h and 7d `used_percentage`, the 5h reset
  time, and each line's pp delta since the run's last report (omitted on the first) —
  from the rate-limit reader below. Label as usage-limit percentages, not cost. On
  Codex and Antigravity the usage reader is N/A — report tokens only.

When the cache is unavailable, report tokens only plus "for your limit %, run
`/usage`". Exact report layout: `references/progress-and-usage.md`.

## Continuous execution

Waves run back-to-back with no pause for permission between them. Stop only on one of
these four conditions (verbatim from spec §6):

1. Blocked with a ⚠️ the controller cannot resolve.
2. A plan contradiction is discovered.
3. Third failure at the same task (after the two-failure escalation above has already
   been used).
4. User interrupt.

No other reason pauses a wave. "This feels like a good stopping point" is not one of
the four.

## Rate-limit reader (Claude)

waves reads real usage from the file at the `rate-limits-cache` key (`## Budget` section
of `docs/agents/galdr.md`, written by setup — cite the config, never a literal path). It
parses `five_hour.used_percentage`, `seven_day.used_percentage`, `resets_at`, and
`cached_at`. The Claude statusline writes this file; galdr never queries an API. This
reader is Claude-only (N/A on Codex and Antigravity). Treat the data as **unavailable**
— never error, never block — when the file is missing or when `cached_at` is older than
the `rate-limits-max-age` key (seconds). Exact read, staleness, and fallback steps:
`references/progress-and-usage.md`.

## Soft park — the pre-dispatch budget guard

Before each not-yet-started dispatch, waves may soft park instead of dispatching.
Soft park's triggers are exactly these three:

- **Usage limit warning** — a usage limit warning appears this session.
- **Quota threshold (Claude only)** — the rate-limit reader shows
  `five_hour.used_percentage` at or above the `five-hour-park-pct` key, or
  `seven_day.used_percentage` at or above the `seven-day-park-pct` key (`## Budget`
  section — cite the config, never a literal). Statusline-cache dependent, so it is
  Claude-only and inactive on Codex/Antigravity; the other two apply on all runtimes.
- **User says "park it".**

Soft park is graceful: in-flight dispatches always finish — reviewed, gated, committed
— before the next dispatch parks; never interrupt one in flight. That waiting rule is
scoped to soft park alone. Urgent triggers — a battery/shutdown warning, a hard limit
already hit, user says "park now" — are continue's hard park (`skills/continue/SKILL.md`
§6), which never waits. Park (soft or hard) is a session end, not a stop condition —
it sits outside the four-condition stop list above.

On park, waves emits one inline line naming the wave and task it parked at plus "run
`/galdr:continue` after your limit resets". The durable resume header is written by
continue's hard park (`skills/continue/SKILL.md` §6), not here.

## Git discipline

- Subagents commit their own work as they reach each green pair — the controller does
  not hold their changes and batch-commit at the end. A task returns `complete` only
  with its commits already made (status contract above); uncommitted work is not done.
- Subagents commit only inside their declared write-scope. Never outside it, even for a
  one-line fix noticed in passing — report it instead of touching it.
- Subagents never push. Subagents never open a pull request. No exceptions.
- While any dispatched agent is in flight in a repo, the controller performs no git
  operations in that repo — no commits, no checkouts, no merges — until every dispatch
  in the wave has returned. One stated exception: a hard park's `wip:` commit — the
  session is about to die; the collision risk is accepted and recorded via the
  `LOST-RISK` lines. This rule keeps the controller from colliding with the subagents'
  own commits; it is not a reason to defer committing to the end.

## Research-brief variant

Research-task briefs add primary-source ownership, per-claim citation, and a committed
artifact — the three bullets are in `references/runtime-dispatch.md`. Dispatch, the
status contract, and the review gate all apply unchanged.

## Reference

`references/agent-brief-template.md` — the brief template every dispatch fills in.

`references/progress-and-usage.md` — the exact rate-limit cache read, staleness and
fallback logic, and the gate/run-end usage report layout.

`references/runtime-dispatch.md` — the per-runtime dispatch, progress-tree, and
usage-reader detail table.
