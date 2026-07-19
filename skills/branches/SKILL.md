---
name: branches
description: Use when starting work on a new branch or worktree, or when a branch's implementation is done and it needs gates, review, a smoke sheet, and a decision about merge/push. Invoke via route or explicit command.
---

# branches

Covers the whole bracket around a branch's work: setting up a worktree at the start,
and finishing the branch at the end (gates, invariants, review, smoke sheet, and the
merge/push decision). Conflict resolution applies whenever a merge or rebase hits one.

## Worktree setup

Detection ladder — ask these in order before creating anything:

1. **Does a worktree for this branch already exist?** Check with `git worktree list`.
   Reuse it. Do not create a second worktree for the same branch.
2. **Is the base clean?** See the clean-baseline rule below. Do not start work on a base
   whose own state is unknown.
3. **Does `.gitignore` cover what this task will generate?** Build output, generated
   clients, `node_modules`. An artifact that isn't gitignored becomes a merge conflict
   later — add the entry before the first commit, not after.

Per-repo setup notes come from `docs/agents/galdr.md`'s `## Worktree notes` section
(package manager, env files, service dependencies). Typical shape:

- Frontend worktree: `pnpm install` before the first run — each worktree has its own
  `node_modules`, not shared with the main checkout.
- Backend worktree: copy `.env` from the main checkout — it's untracked, so
  `git worktree add` does not carry it.
- Docker-dependent repos: note which services each worktree needs. Multiple worktrees
  usually share one compose stack run from the main checkout; don't start a second
  stack per worktree unless ports collide.

One worktree per parallel implementer when write-scopes demand it: if a wave's
plan-time partition check found write-scopes that can't share one working tree (they'd
step on each other's uncommitted changes), give each implementer its own worktree so
each can commit independently.

## Clean-baseline rule

Before starting work, run the full gate manifest once against the base and record the
result (a WIP line or a note in memory-progress.md). That result is the baseline. If
something is already failing at this point, it was failing before this branch existed —
attribute it to the base, not to this branch. Still report it; a pre-existing failure
is a finding, not something to bury under "not my branch's problem."

## Commit discipline

Commits made directly on the branch outside a task loop — worktree setup, a doc or
config change, a conflict resolution — follow the same atomic rule as task commits: one
logical change per commit, conventional prefix
(`feat`/`fix`/`refactor`/`test`/`docs`/`chore`), never mixed. Task commits inside a wave
already get this from tdd and the brief's commit rules; `wip:` stays reserved for
parking unfinished state (see continue).

## Finish procedure

Finishing a branch runs this sequence, in order:

1. **Full gate manifest** — the verify skill's branch-finish proportionality: full
   manifest + invariants + e2e where configured. Run it now; a stale run from earlier
   in the session doesn't count.
2. **Invariant checks** from `docs/agents/galdr.md`'s `## Invariants` section, if any
   are configured for this repo.
3. **Branch-level review** (the review skill) — both axes, forced verdicts.
4. **Smoke sheet** (below).
5. **Default outcome**: keep the branch, write the finish report, append a closeout
   line to memory-progress.md — beginning with the `CLOSEOUT` (or, at release, `RELEASED`)
   marker that `continue` §7's rotation boundary scans for — and advance the spec's
   `Lifecycle status:` line to `shipped` — which marks the branch's work finished, not
   that it merged (merge and push stay separate, below). This is the default outcome
   every time — finishing does not merge and does not push (see Consent below).
6. **Progress-log rotation** — after the closeout line is written, rotate
   `memory-progress.md` per `skills/continue/SKILL.md` §7 (Progress-log rotation).

When you defer something at finish rather than fixing it now, append it to the backlog
per /galdr:backlog (skills/backlog/SKILL.md) — don't restate the format here.

The finish report shown to the user contains, inline and in this order: (a) a change
summary — the commit list, files touched, and what changed behaviorally, in a few
plain sentences; (b) both review verdicts; (c) the smoke sheet's full content, not
just its file path — the user walks it from the report, without opening files; (d) the
open backlog items, listed via /galdr:backlog (skills/backlog/SKILL.md), with an offer
to pick one up next — never auto-start one. The sheet is still written to its file (the
durable copy); the report is where it is read.

A Critical finding from steps 1-3 stops the sequence there: fix it before producing the
smoke sheet or the report.

## Smoke sheet

After gates and review pass, produce a smoke sheet — a file a person can read and click
through to confirm the change actually works, because a green suite does not prove the
UI or the API behaves correctly.

**Location:** the path named in `docs/agents/galdr.md`'s `## Smoke` section, under
"smoke-sheet output dir." Default when unset: `docs/agents/smoke/<date>-<branch>.md`.

**Contents, in this order:**

1. Launch instructions, copied verbatim from `## Smoke` (launch command, base URL, test
   account / seed-data notes). Copy them exactly; don't paraphrase a command.
2. User-visible changes, ranked biggest-first: the change a person would notice first
   (the "WOW item") goes at the top; cosmetic or backend-only changes go at the bottom.
3. For each item, an exact click path: URL, route or page, panel or component name —
   specific enough to follow without re-deriving it from the diff.
4. Test-data prerequisites per item, when the click path needs one (a seeded account, a
   specific product, a feature flag).
5. **API-only fallback**: when a change has no user-visible surface at all
   (backend-only, internal refactor, migration), skip the click-path list and give a
   curl example per changed endpoint or behavior instead — one example request and its
   expected response.
6. Screenshots, attached when browser tooling is available this session; when it isn't,
   say "screenshots not available this session" rather than leaving the point silent.

The finish report's last line is always: "open `<base URL>` and walk the sheet" — the
actual base URL from the config, not a placeholder.

A change with zero user-visible surface still gets a sheet — item 5 above is what makes
it non-empty. Never skip the smoke sheet because "nothing to click."

## Consent: merge and push

Finishing a branch never merges or pushes by itself.

- Do not merge without the user's explicit go on this specific branch. "Tests are green" or
  "the review passed" is a finish-procedure result, not a merge instruction — it does
  not substitute for the go.
- Do not push, and do not open a PR, without authorization for this specific action at
  the time of the action. A go from a previous session or a previous branch does not
  carry forward.

The default outcome is keep the branch, report, and closeout line — stated once here,
applies every time, no exceptions.

## Destructive operations

Worktree removal with uncommitted work, and branch deletion, both require typed
confirmation before the command runs: ask the user to type the exact branch or worktree
name back. "Yes" or "go ahead" is not typed confirmation — the name itself is.

No controller git operations in a repo while a dispatched agent is working there (a
waves dispatch or brief in flight). Wait for it to return before touching that repo.

## Conflict resolution

When a merge or rebase hits a conflict:

1. **Intent archaeology first.** Read both sides' commits for what each was trying to
   do — commit messages, the branch's own plan or spec, surrounding code — before
   touching a conflict marker. The diff lines alone don't tell you intent.
2. **Stated-goal tie-break.** When both sides plausibly intended something reasonable,
   resolve toward whichever matches the current task's stated goal (the plan or spec
   driving this branch) — not whichever side is larger or arrived first.
3. **Never invent behavior mid-merge.** If intent isn't clear from the archaeology,
   stop and ask. Writing new logic to paper over an unclear conflict is worse than
   leaving it unresolved.
4. **Regenerate, don't hand-merge, generated artifacts.** Lockfiles (`pnpm-lock.yaml`),
   generated code (`wire_gen.go`, generated API clients) never get hand-edited at a
   conflict marker. Resolve the source inputs on both sides, then regenerate the
   artifact with the tool that produces it.
5. **Semantic-conflict gate.** A clean merge (no conflict markers) is not proof the
   result is correct — two branches can each pass their own tests and still break each
   other's assumptions. Re-run the full gate manifest on the merged result even when
   git reports zero conflicts.
6. **Mid-rebase WIP line.** Before starting a rebase, write a WIP line to
   memory-progress.md naming the branch and the operation in progress (for example,
   "rebasing `<branch>` onto `<base>`"). If the session dies mid-rebase, the next
   session runs `git status` to read the actual rebase state rather than trusting the
   WIP line's prose.
