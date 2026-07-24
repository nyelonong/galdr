# Runtime dispatch detail

The per-runtime detail for waves: dispatch mechanism, progress-tree mechanism, and
usage reader. The `waves/SKILL.md` body names one concrete mechanism per runtime inline;
this file holds the full table, the per-runtime recipes, and detail the body points
here for its line budget. It is one hop — no further reference files.

## Per-runtime table

| Runtime | Dispatch | Progress tree | Usage reader |
|---|---|---|---|
| Claude | Workflow tool (preferred) or Agent tool — one call per frontier task in the same response, so they run in parallel | TodoWrite — seed one `pending` per task, flip frontier to `in_progress` at wave open, set final status at the wave gate | statusline rate-limit cache at the `rate-limits-cache` key |
| Codex | subagents — the AGENT-BRIEF is the dispatch prompt: spawn one agent per brief, wait for all to return, then return a summary. `/agent` to inspect a running or returned agent | the Codex task view — same seed/flip/final cadence as TodoWrite | N/A |
| Antigravity | `start_subagent` — dynamic subagents, isolated context, parallel | the Antigravity agent view — same seed/flip/final cadence | N/A |

All three run the same dispatch procedure, status contract, and review gate from
`skills/waves/SKILL.md`. The runtime only changes how the calls go out.

## Effort support by dispatch mechanism

Whether a binding's effort half reaches the dispatch, per mechanism:

- **Workflow tool** — effort settable per agent; pinned alongside the model when the
  wave is written as a script.
- **Agent tool** — not settable. The dispatch carries model only; the WIP line and any
  EV line record `effort=n/a`.
- **Codex subagents** — not settable. The AGENT-BRIEF carries model only; the WIP line
  and any EV line record `effort=n/a`.
- **Antigravity `start_subagent`** — not settable. The dispatch carries model only; the
  WIP line and any EV line record `effort=n/a`.

## Claude: Workflow vs Agent tool

Check once per wave: does a Workflow tool appear in the available tools this session?

- **Workflow tool present (preferred)** — write the wave as a script: fan out the
  frontier, pin each task's model and effort, encode the gates as code. Deterministic;
  use this mode when the tool is present. One workflow per wave; refresh the TodoWrite
  tree at each wave boundary.
- **Agent tool only** — dispatch one Agent-tool call per frontier task in the same
  response, so they run in parallel. Update the TodoWrite tree per task as returns
  land.

Token source differs: Workflow mode takes per-wave tokens from the workflow-completion
`subagent_tokens`; Agent-tool mode sums the usage reported by each Agent return.

## Codex: subagents

The AGENT-BRIEF is the dispatch prompt. For each brief: spawn one agent, wait for all
agents in the wave to return, then return a summary. Use `/agent` to inspect a running
or returned agent. The Codex task view replaces TodoWrite at the same cadence. The
usage reader is N/A — report tokens only, no limit percentages.

## Antigravity: start_subagent

`start_subagent` dispatches dynamic subagents with isolated context in parallel. The
Antigravity agent view replaces TodoWrite at the same cadence. The usage reader is N/A
— report tokens only, no limit percentages.

Subagent returns surface as native reviewable code diffs. Two binding rules from the
skill body still apply: the `EV`/`memory-progress.md` ledger is written, and the hard
gate is not skipped by an "Always Proceed" policy. Review each diff against the brief's
acceptance criteria before the task can be marked `complete`.

## Soft-park trigger portability

- **Usage limit warning** — applies on all three runtimes (reactive).
- **User says "park it"** — applies on all three runtimes (reactive).
- **Quota threshold** — Claude only, since it depends on the statusline rate-limit
  cache. On Codex and Antigravity this trigger is inactive; the other two still apply.

On Claude Workflow mode, waves also stops launching not-yet-started `agent()` calls
once a soft-park trigger fires. Dispatches already in flight always finish and are
reviewed, gated, and committed first — soft park's waiting rule; continue's hard park
never waits.

## Research-brief variant

When a task is a research task rather than an implementation task, its brief adds:

- **Primary-source ownership** — cite the primary source itself, not a summary of it,
  wherever a primary source exists.
- **Per-claim citation** — every claim in the returned artifact carries its source
  inline, not gathered into a bibliography at the end.
- **Artifact committed to the repo** — the research output is a file committed at a
  path the write-scope names, not left only in the subagent's transcript.

Dispatch, the status contract, and the review gate all apply unchanged.
