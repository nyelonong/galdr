## 0.14.0 – 2026-07-24

- `release.sh`: dev-only, repo root, the whole release sequence behind five
  preflight checks (clean working tree; version consistency read from the
  branch's own files across plugin.json, the README badge, and the CHANGELOG
  heading; tag-collision, local and origin; main-not-diverged; the full gate
  suite) then, unless stopped, ff-merge, a post-merge re-gate, an annotated
  tag, a push, `./publish.sh`, and a bookkeeping reminder. `--preflight` runs
  every check and stops before any mutation, exit 0. Proven by an 11-fixture
  TDD harness (`testing/release-test.sh`), each fixture a disposable mktemp
  dev repo plus bare origin, never touching the real repo or its remotes.
- `usage-bridge status` subcommand: `scripts/usage-bridge.sh status` reports
  three fixed lines (installed, cache, original statusline) and exits, never
  reading stdin. `/galdr:doctor` check 5 now reports the real install state
  through this subcommand; the doctor script itself is unchanged.
- the 5 retrieval spot-checks owed since the auto-effort revert cycle are
  cleared: all 5 run clean-room per `testing/protocol.md` §2 (fresh subagents,
  no path-based rule injection), 3 passing first-pass and 2 on a fresh re-probe
  after a narrower first reading.

## 0.13.0 – 2026-07-24

- `/galdr:doctor` + `scripts/galdr-doctor.sh`: a wiring diagnostic, 6 checks
  (enabled-flag, hook-registered, emission, version, usage-bridge, repo-config),
  exit 1 only when wiring is genuinely broken (a FAIL), exit 0 on OK-only or
  ADVISE/N/A-only runs; the script never remediates, every non-OK detail line
  names the exact fix command for the user to run. Proven by an 8-fixture TDD
  harness (`testing/galdr-doctor-test.sh`), each fixture a fresh `mktemp -d` tree,
  never touching the real `$HOME` or plugin root.
- backlog `list` action gains an OVERDUE aging flag: an Open item ages when its
  target provably lies in the past, a version target against the repo's version
  source (`plugin.json`, else the newest semver git tag) at target ≤ current
  version, or a date target before today; free-text targets ("later", "only if
  ever needed") and version targets in a repo with no version source are
  exempted, never flagged. The flag marks the listing line
  `OVERDUE (target <t>, now <v>)` and never edits or auto-resolves the item.
- `/galdr:retro`: reads `memory-progress.md` and `memory-progress-archive.md` back
  in aggregate across closed cycles and reports five metric families (tier
  escalations, review verdicts, trust gap, interruptions, spend), proposes at
  most 3 recommendation-first tunings each naming its exact target line, and
  applies nothing to the repo or its config on its own.
- `branches` finish now proposes running `/galdr:retro` on the fresh ledger at a
  `RELEASED` closeout, a proposal in the report only, never auto-run.
- roster: 18 → 20 skills (`doctor`, `retro`).
- auto (model, effort) tiering removed, one release after it shipped in 0.9.0. Three reasons, in the order they hurt: dispatches were rejected over their effort value, the tier defaults picked worse effort levels than the session dial would have, and the surface it added (a config suffix, three ledger fields, a fourth ladder rung, a rejection-fallback rule, and a per-mechanism support table) cost more to carry than it returned. The session's own `/effort` dial governs every dispatch again.
- `docs/agents/galdr.md` §Models rows go back to `tier → model`. A row that still carries an `@ <effort>` suffix from an older config is read by ignoring the suffix: no error, no warning, no migration pass. `setup` drops it the next time it rewrites the section.
- the escalation ladder is `mechanical → standard → top` with a uniform three-attempt budget at every tier: retry, then escalate one tier and retry once, or retry at the same tier when already at `top`. Every runtime reads it the same way; the `top@max` rung and its no-effort-runtime carve-out are both gone.
- the dispatch WIP line carries `tier=` and `model=` only, and `attempt=` EV lines carry the tier with no effort suffix. The effort-rejection EV line is removed with the rule it recorded.
- `plan`'s per-task override is `**Model tier:** <tier>`, only when it overrides the default.
- kept, with only the effort half dropped: `shape`'s independent spec-review dispatch, and activity rows in §Models. The row reads `spec-review: top` and resolves through the top tier's model.
- `setup`'s confirm step no longer flags suspect (model, effort) pairings; the check existed only for effort.

## 0.11.0 – 2026-07-24

- `testing/pack-lint.sh`: a self-lint gate for the pack, 10 families (budgets, carrier-identity, markers, canon-strings, project-tokens, frontmatter, refs, trailing-newline, em-dash, badges), exit-coded (0 clean, 1 on any violation), report-all (every violation printed in one run, not just the first).
- `testing/pack-lint-test.sh`: a 22-fixture harness proving the linter itself, TDD red-first per family (a fixture seeds the violation, the family's check must catch it; a clean fixture must pass).
- canonical `## Line budgets` table added to `docs/agents/galdr.md`: single source for every SKILL.md budget plus `hooks/bootstrap.md` and `galdr-core.md`, 20 rows; gates rewired to run the one `pack-lint.sh` command instead of the prior scattered checks.
- decision 13: `disable-model-invocation: true` sanctioned as an optional third SKILL.md frontmatter key (alongside `name` and `description`), caught live by the linter's own first real run against the pack.
- em-dash sweep across the 13 pre-0.10 smoke sheets, and a core trailing-newline fix, both closing violations the new linter surfaced.

## 0.10.0 – 2026-07-24

- two-level park: soft (waves' pre-dispatch budget guard: stop before the next dispatch, in-flight work finishes) and hard (continue §6: flush in under two minutes, never wait), resolving the standing contradiction between waves' "in-flight dispatches always finish" rule and continue's under-two-minutes target.
- ledger-scan crash detection: continue §3 gains a file-order scan before acting on any `next:` line: a WIP line with no closure later in the file means the previous session died unplanned and crash recovery runs first; a clean park still leaves zero open WIP, so normal resume is unaffected.
- crash recovery: continue §9: recovers from the ledger and git alone (no transcript salvage), classifies each open dispatch from its own recorded base sha and scope paths, commits a dirty tree as `wip: crash-salvage — <desc>` (labeled UNVERIFIED in the snapshot, never discarded or stashed), and closes each handled WIP line with an `EV [recovery]` line before appending a `CRASH` marker and the handoff snapshot.
- waves gains a per-return closure line, appended after every two-verdict review and before the next dispatch: `EV [waves] <task-id> return reviewed status=<status> @<sha>`.
- continue §2's step-completion summary is now greppable: `DONE <step> — <summary> @<sha>`.
- bootstrap §1 gains a one-clause crash-detection pointer into continue's recovery procedure, applied byte-identically across all four carriers (`galdr-core.md`, `hooks/bootstrap.md`, `carriers/codex.md`, `carriers/antigravity.md`).
- `testing/scenarios/continue.md` gains a crash-resume pressure scenario and a hard-park scenario; the `guard-trigger` spot-check is updated to the soft/hard trigger split; waves' retrieval spot-check probe is updated to cite the closure-line rule and soft-park naming.

## 0.9.0 – 2026-07-23

- auto (model, effort) tiering: `docs/agents/galdr.md` §Models gains a `(model, effort)` row schema with an inherit rule; `setup` writes model+effort defaults and adds a suspect-combo confirm check; `waves` assigns each task a (tier, effort) binding, escalates on 2 consecutive fails through a ladder ending at `top@max`, and records the effective binding in the ledger (`tier=`/`model=`/`effort=`, `attempt=` EV lines, effort-rejection fallback); `plan` supports a per-task `**Model tier:** <tier> [@ <effort>]` override; `shape` dispatches spec-review as an independent step (Workflow-mode only).

## 0.8.3 – 2026-07-20

- `galdr:plan` now emits a Mermaid DAG diagram of the plan's waves (one `subgraph` per wave, one node per task, edges only for blocking dependencies that cross a wave boundary), placed right after the Progress table. Generated once from the same task list as the rest of the plan file; not regenerated by `waves` at wave gates.
- `galdr:waves`'s usage-and-token report now shows a percentage-point delta on the 5h/7d usage-limit lines, against the run's own previous printed reading. Omitted on a run's first reading; a gate where the rate-limit cache was unavailable contributes no reading and is skipped rather than counted as a 0pp move.

## 0.8.2 – 2026-07-20

- `memory.md`'s Current State section now rotates: restructured from one continuous, unbounded paragraph into one paragraph per release; the last 3 stay inline, older ones move to a new `memory-archive.md` (new `continue` §8). Applied immediately to this repo's own memory.
- `scripts/roles-touched-check.sh` gained a `--range <rev-range>` mode: scans only the `docs/specs/` files changed within a git revision range instead of the whole directory.
- removed the stale `reserve-key` scenario from `testing/scenarios/setup.md` (tested a Budget key dropped from the skill entirely in 0.6.1, with no replacement. Budget already has real coverage elsewhere).
- `continue` added to the discipline-skill list in `CLAUDE.md`, `testing/protocol.md`, `docs/agents/galdr.md`, and `skills/authoring/SKILL.md`. It was pressure-tested from the pack's original build, but 4 documentation lists never named it.

## 0.8.1 – 2026-07-20

- `setup` respects deliberately-removed Budget keys: a user-deleted key (e.g. `rate-limits-max-age`) no longer gets silently re-added on the next `/galdr:setup` re-run, mirroring the existing Gates/Invariants Human-edits protection (without needing the extra diff-and-confirm step, since nothing is being overwritten when a key is simply absent).
- fixed a stale `testing/scenarios/setup.md` assertion (`usage-config`'s expected `seven-day-park-pct` default was `90`; the real default has been `95` since 0.6.1) and added a new scenario covering the Budget-key-removal behavior.

## 0.8.0 – 2026-07-20

- roles-and-journeys: `setup` gains a 5th step: an interview that reads a target repo's own docs/specs/code first, drafts what it finds, interviews only for gaps, and writes a cited-only `docs/agents/roles-and-journeys.md` (never inventing an unsourced claim). `shape` gains a matching "Roles touched" field and a 5th self-review point that catches a spec drifting from that doc, stopping synthesis on conflict rather than silently proceeding. A shipped script, `scripts/roles-touched-check.sh`, adds a non-semantic CI backstop (presence, not meaning). galdr itself has no product roles and is not a target for the doc this feature generates.
- `/galdr:core install` auto-detect: the invoking agent now determines its own runtime from its own operating context and passes it as `[agent]`, instead of defaulting to `codex` and requiring the user to always name it explicitly.
- two stale `testing/scenarios/waves.md` spot-checks fixed to match `waves`' post-0.7.0 shape (a renamed heading, per-runtime cadence detail that moved to a reference file); `testing/scenarios/core.md` added, closing the gap where `core` had a shipped-bash test but no retrieval spot-check coverage.
- `waves`' usage/token report is now required to be printed in the response to the user at every wave gate, not just logged as an `EV` line to the ledger. Closes an ambiguity that let the two get conflated.
- README/CLAUDE.md stale-doc fixes carried over from 0.7.0 (version badge, skill count, `core` missing from the skill table).

## 0.7.0 – 2026-07-19

- multi-agent installability: galdr is now runtime-neutral across Claude, Codex, and Antigravity.
- canonical `galdr-core.md` plus three carriers (`hooks/bootstrap.md` for Claude, `carriers/codex.md` → `~/.codex/AGENTS.md`, `carriers/antigravity.md` → `~/.gemini/AGENTS.md`); each reproduces the §0–§6 block byte-identical, enforced by a content-anchored canon grep in the gate.
- `/galdr:core` installer (`install|uninstall|status` per agent: `claude`, `codex`, `antigravity`): consent-before-write, idempotent marked-block replacement, atomic writes, reversible; unifies all three enables under one command.
- runtime-gap and Antigravity artifact notes across six skills (`waves`, `usage-bridge`, `setup`, `plan`, `verify`, `branches`): per-runtime dispatch (Claude Workflow/Agent tool, Codex subagents, Antigravity `start_subagent`), Claude-only markers, and Antigravity native Artifacts (Task List + Implementation Plan, reviewable code diffs, browser verification, Walkthrough) as the human-facing surface, additive to the durable text ledger, never replacing it.
- multi-agent install via `npx skills add nyelonong/galdr` (skills on all three runtimes) plus `/galdr:core install <agent>` (always-on core per agent).
- live smoke: Claude Code verified this cycle (`/galdr:core install claude` enables the hook; the injected core is byte-identical to `galdr-core.md`; a live four-wave parallel `waves` run dispatched, reviewed, and gated). Codex and Antigravity are not yet smoked this cycle. Runbook sheets at `docs/agents/smoke/2026-07-19-0.7-codex.md` and `…-antigravity.md` are recorded as untested, not passed.

## 0.6.1 – 2026-07-19

- setup Budget config simplified: dropped the `reserve-per-task` key (a Workflow-mode-only token-budget guard); `setup` now writes four Budget keys. `seven-day-park-pct` now defaults to `95` (the 7-day budget recovers more slowly than the 5-hour). waves drops the dependent "budget below reserve" park trigger; three park triggers remain (usage-limit warning, "park it", 5h/7d quota threshold).

## 0.6.0 – 2026-07-19

- progress-log rotation: at branch finish, closed cycles (through the last `CLOSEOUT`/`RELEASED` marker) move to an append-only `memory-progress-archive.md`; the live `memory-progress.md` keeps the newest `next:`, open WIP, and a one-line archive pointer, so the resume read stays fast and `EV` history is preserved across both files.

## 0.5.1 – 2026-07-19

- enable flag moved to a stable path (`~/.claude/galdr/enabled`) so the always-on core stays enabled across plugin updates. No more re-enabling after every version bump. The legacy in-plugin `hooks/enabled` is still honored for back-compat.

## 0.5.0 – 2026-07-19

- backlog capture: a `/galdr:backlog` skill owns docs/backlog.md (list open items, defined entry format, resolve); shape/plan/waves/review/branches append deferrals to it automatically; branches finish proposes the open items at cycle end.

## 0.4.0 – 2026-07-19

- usage-bridge installer (`/galdr:usage-bridge install|uninstall|status`): an opt-in, reversible statusline wrapper that writes the rate-limits cache so any machine gets the real 5h/7d usage % and the quota-threshold park.

## 0.3.0 – 2026-07-19

- live progress tree: waves maintains a native TodoWrite task list mirroring the plan's tasks, so progress shows in the main view across execution modes.
- usage & token reporting: at each wave gate and run end, waves reports tokens spent plus the real 5h/7d limit % (read from the statusline rate-limits cache; falls back to tokens + /usage when absent).
- rate-limit-aware budget guard: the pre-dispatch guard parks when the 5h or 7d used % crosses a configured threshold.

## 0.2.0 – 2026-07-19

- waves pre-dispatch budget guard: parks gracefully before a dispatch it cannot finish (Workflow-mode budget signal / limit warning / "park it"), resumable via /galdr:continue
- live per-task progress table at the top of the plan doc, regenerated by waves at each wave gate from memory-progress.md; spec carries a one-line lifecycle status

## 0.1.0 – unreleased

- Wave 0: Scaffold and test harness

### Build record (waves 0-4 audits, 2026-07-18/19)
- Wave 0: scaffold, continuation files, testing protocol.
- Wave 1: bootstrap (46 lines) + enforced core (using-galdr, route, tdd, verify, continue), pressure-tested; route accuracy 15/15 after key correction.
- Wave 2: orchestrators (shape, plan, waves, review, debug, branches), debug pressure-tested, five spot-checks, four review fixes re-reviewed.
- Wave 3: user-only skills (prototype, rearchitect, authoring, setup), four reviews clean, spot-checks 4/4.
- Wave 4 audits: pack total 1,934 lines; standing context ≈1,240 tokens (< 2,000 ceiling); full-pack router accuracy 16/16 after spec-first key amendment (zero fast-path violations across all runs).

## 0.1.0 – 2026-07-19

Released after the trial-run gate: a real production task executed end-to-end
through galdr on a private backend repo: route → shape-synthesis → plan → Workflow-mode waves
(RED-first TDD, atomic commits) → wave gate (0 new failures vs base) → two-axis review
(Standards PASS / Spec PASS WITH NOTES, plan-is-the-bug flow exercised) → finish
(keep+report + smoke sheet, walked and confirmed). Cutover: hook enabled, superpowers
uninstalled, mattpocock skills disabled. Post-trial fixes: decision 19 (finish report
inline), spec-location and ledger-commit lessons in the issues log for 0.1.1.
