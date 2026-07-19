---
name: waves
description: Use when a plan already exists and is ready to run — dispatches each wave's tasks, reviews every return before trusting it, and gates advancement on evidence. Invoke via route or explicit command.
---

# waves

waves executes the task list a plan produced: wave by wave, dispatching each wave's
frontier, distrusting every report until it's checked, and gating the next wave on
evidence instead of a claim.

## Execution modes

Two first-class modes. Check once per wave: does a Workflow tool appear in the
available tools this session?

- **Workflow-tool script** (when the tool exists): write the wave as a script — fan out
  the frontier, pin each task's model and effort, encode the gates as code.
  Deterministic; use this mode when the tool is present.
- **Agent-tool dispatch** (when it isn't): dispatch one Agent-tool call per frontier
  task in the same response, so they run in parallel.

Both modes run the same dispatch procedure, status contract, and review gate below —
the mode only changes how the calls go out.

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
   format): `**WIP** dispatched <brief path> @<base sha> scope=<paths> — next: review
   on return`.
3. Dispatch with the declared write-scope as the only paths the subagent may touch.
4. On return, run the two-verdict review below before acting on anything the report
   claims.

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

Severity within either verdict: Critical findings get fixed now, before the task can be
marked `complete`. Important findings get fixed before the next task starts. This
mirrors the severity gate the review skill uses at branch level.

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

## Model tiers

- Mechanical tasks (brief marked `mechanical: true`) → haiku.
- Standard implementation and per-task review → sonnet.
- Planning, wave-gate review, and debug → the session model.

Failure escalation at a single task:

1. First failure: retry on the same tier.
2. Second failure at the same task: escalate one model tier, retry once.
3. Third failure at the same task: stop the wave. This is one of the four STOP
   conditions below — the escalation path ends here, at two tries.

Tier→model-id bindings (which literal model haiku/sonnet/session map to) are read from
the repo's `docs/agents/galdr.md` config, written by setup; defaults are named in setup
itself (task 3.4), not here — models change, skill text shouldn't.

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
   memory-progress.md.

A wave gate that produced no EV lines has not happened, regardless of what the dispatch
reports said. Defer a task to a later cycle? Append it to the backlog per /galdr:backlog
(skills/backlog/SKILL.md).

## Live progress table

The plan's `## Progress` table (format defined in `skills/plan/SKILL.md`) is a derived
view waves maintains — never hand-edited, since `memory-progress.md` stays the durable
state:

- **Wave open** — mark the wave's frontier tasks `in-progress`.
- **Wave gate** — regenerate the whole table from `memory-progress.md`.
- **First dispatch of the run** — advance the spec's `Lifecycle status:` line to
  `in-progress`.

Both table writes happen only at points the controller may already write the repo (wave
open, wave gate) — never while a dispatch is in flight.

### Native task tree

Alongside the plan table, waves keeps a native TodoWrite list mirroring the plan's tasks:
seed one `pending` entry per task at run start; flip a wave's frontier tasks to
`in_progress` at wave open; set each to its final status at the wave gate. In Workflow
mode waves runs one workflow per wave, so the controller refreshes the tree at each wave
boundary; in Agent-tool mode it updates the tree per task as returns land. The TodoWrite
tree is an ephemeral mirror — `memory-progress.md` stays the only durable state.

## Usage and token report

At each wave gate and at run end, waves reports together:

- **Tokens** — spent this wave plus running cumulative: from each workflow-completion's
  `subagent_tokens` in Workflow mode, or summed from each Agent return's usage in
  Agent-tool mode.
- **Usage limits** — the real 5h and 7d `used_percentage` and the 5h reset time from the
  rate-limit reader below. Label these as usage-limit percentages, not a dollar cost.

When the cache is unavailable, report tokens only plus the line "for your limit %, run
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

## Rate-limit reader

waves reads real usage from the file at the `rate-limits-cache` key (`## Budget` section
of `docs/agents/galdr.md`, written by setup — cite the config, never a literal path). It
parses `five_hour.used_percentage`, `seven_day.used_percentage`, `resets_at`, and
`cached_at`. The statusline writes this file; galdr never queries an API. Treat the data
as **unavailable** — never error, never block — when the file is missing or when
`cached_at` is older than the `rate-limits-max-age` key (seconds). The reader feeds the
usage report above and the quota trigger below. Exact read, staleness, and fallback
steps: `references/progress-and-usage.md`.

## Pre-dispatch budget guard

Before each not-yet-started dispatch, waves may park instead of dispatching. Three
triggers:

- **Usage limit warning** — a usage limit warning appears this session.
- **User says "park it".**
- **Quota threshold (both modes)** — the rate-limit reader shows
  `five_hour.used_percentage` at or above the `five-hour-park-pct` key, or
  `seven_day.used_percentage` at or above the `seven-day-park-pct` key (`## Budget`
  section — cite the config, never a literal). This trigger works in both execution
  modes; when the cache is unavailable it is simply inactive and the other triggers
  still apply.

Park is graceful. Dispatches already in flight always finish and are reviewed, gated,
and committed first — never interrupt an in-flight dispatch. Only then does waves park,
before the next dispatch. In Workflow mode, waves also stops launching not-yet-started
`agent()` calls once a park trigger fires.

On park, waves emits one inline line naming the wave and task it parked at plus "run
`/galdr:continue` after your limit resets". The durable resume header itself is written
by continue's limit-park (`skills/continue/SKILL.md` §6), not here.

**Mode scope:** the usage-limit-warning and "park it" triggers are reactive and apply in
both modes; in Agent-tool mode waves parks at wave boundaries. The quota-threshold
trigger is checked before every dispatch in both modes.

## Git discipline

- Subagents commit their own work as they reach each green pair — the controller does
  not hold their changes and batch-commit at the end. A task returns `complete` only
  with its commits already made (status contract above); uncommitted work is not done.
- Subagents commit only inside their declared write-scope. Never outside it, even for a
  one-line fix noticed in passing — report it instead of touching it.
- Subagents never push. Subagents never open a pull request. No exceptions.
- While any dispatched agent is in flight in a repo, the controller performs no git
  operations in that repo — no commits, no checkouts, no merges — until every dispatch
  in the wave has returned. This rule keeps the controller from colliding with the
  subagents' own commits; it is not a reason to defer committing to the end.

## Research-brief variant

When a task is a research task rather than an implementation task, its brief adds:

- **Primary-source ownership** — cite the primary source itself, not a summary of it,
  wherever a primary source exists.
- **Per-claim citation** — every claim in the returned artifact carries its source
  inline, not gathered into a bibliography at the end.
- **Artifact committed to the repo** — the research output is a file committed at a
  path the write-scope names, not left only in the subagent's transcript.

Dispatch, the status contract, and the review gate all apply unchanged.

## Reference

`references/agent-brief-template.md` — the brief template every dispatch fills in
before it goes out.

`references/progress-and-usage.md` — the exact rate-limit cache read, staleness and
fallback logic, and the gate/run-end usage report layout.
