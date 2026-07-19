# galdr

**One methodology pack that takes a rough idea all the way to a reviewed, merged branch — a failing test before every line, fresh evidence before every "done," and a memory that survives a dead session.**

*galdr* — Old Norse for "incantation." A personal engineering methodology for Claude Code: routed requests, wave-based TDD-first plans, evidence gates, subagent execution, and durable memory.

---

## Why I built this

I was running two skill packs at once — overlapping bootstraps, competing conventions, and a standing context cost I paid on every single session. Neither matched how I actually work: shape an idea into a spec, turn it into a wave-based TDD plan, run it with subagents behind evidence gates, and keep durable memory so nothing is lost across a `/clear` or a dead session.

So I built one pack that *is* that method — small enough to leave on all the time, and held to the same standard it holds your code to: every discipline rule was tested against an agent that didn't have it before it shipped.

## What it does

galdr routes every substantive request to the right amount of process — no more, no less — then runs a disciplined path from idea to merge.

**The main flow**
- **`shape`** — turns a fuzzy idea into a written spec. Grills you one decision at a time, each with a recommendation, until nothing is ambiguous.
- **`plan`** — turns the spec into a wave-based task DAG: write-scoped, independently testable tasks with declared dependencies.
- **`waves`** — executes the tasks with subagents, wave by wave, gating each wave on real evidence, not a subagent's "done."
- **`review`** — a fresh-context reviewer checks the work against the spec first, then against code quality.
- **`branches`** — finishes: full gate run, a manual smoke sheet, and a merge/push decision that is always yours.

**Always on, inside every task**
- **`tdd`** — no production code without a failing test first.
- **`verify`** — no "done" without fresh evidence, skip-count included (a silently-skipped suite is not a green suite).
- **`debug`** — no fix without a root cause.

**What keeps it honest**
- **Evidence gates.** Every RED, GREEN, gate, and review verdict is a greppable `EV` line in `memory-progress.md`, tied to the commit that produced it.
- **Durable memory.** State lives in `memory.md` and `memory-progress.md`. A new session reads them first and re-verifies claims with commands — so work survives `/clear`, compaction, and session death.
- **Usage-aware.** A pre-dispatch guard parks the run before it burns past your 5-hour / 7-day limit and resumes cleanly; each wave reports tokens spent and your real usage %.
- **A self-managing backlog.** Deferred work is captured automatically and proposed back to you when a cycle finishes — nothing gets forgotten.

## Example: a rough idea, made buildable

Drop a half-formed idea:

> "I think users should be able to export their data."

`/galdr:shape` doesn't start building. It grills — one decision at a time, each with a recommendation you confirm or override:

```
routing: shape-grill — a position to stress-test

Next: which format — CSV, JSON, or both? Recommend CSV first — it's what a
non-technical user opens in a spreadsheet; a JSON export can follow if an API
consumer actually asks. Confirm, or do you need JSON now?
  → CSV

Next: whose data — the user's own records, or everything they can see (team /
shared)? Recommend own records only — it's the clean privacy line and can't leak
a teammate's data. Override?
  → own records

Next: delivery — a direct download, or an emailed link? Recommend a direct
download under ~10k rows and an emailed async link above it — instant for most
people, safe for the large accounts.
  → agreed
```

…and out comes a spec precise enough to hand to any agent — or any engineer — and get exactly the right thing built:

```markdown
# Data export — spec
Goal: let a signed-in user export their own records as a file.

Non-goals: exporting other users' or team-shared data; scheduled / recurring exports.

Constraints:
- own-records-only — an export never includes a row owned by another user.
- format is CSV.
- direct download under 10,000 rows; emailed async link at or above 10,000.

Decisions: format = CSV-first · scope = own-records · delivery = sync-with-async-fallback

Acceptance criteria:
- a user with < 10k rows gets a CSV of exactly their records, nothing else;
- a user with ≥ 10k rows gets an emailed link within the async budget;
- no export ever contains a row owned by a different user.
```

That spec **is** the prompt — unambiguous, testable, and impossible to build two different ways. Everything downstream (`plan` → `waves` → `review`) is checked against it.

## Example: idea to merged branch

The full loop:

```
route → shape (spec) → plan (wave DAG) → waves (subagents, RED-first, evidence gate
per wave) → review (spec + quality) → branches (gate, smoke sheet, merge decision)
```

Every wave dispatches subagents that commit their own atomic red-green pairs; every return is reviewed against its brief before it's trusted; every gate writes `EV` lines. galdr's own `0.2`–`0.5` releases — the budget guard, live progress + usage reporting, the usage-bridge installer, and the self-managing backlog — were each built exactly this way, start to finish.

## Proven, not promised

Every rule in this pack was tested against an agent that didn't have it — the same protocol the pack prescribes for your code, applied to the pack itself.

- **Pressure-tested discipline.** Every discipline skill ran RED first: a baseline agent, no skill, real fixtures. The baselines failed the way real sessions fail — edited production code on a "tests after" nudge, retrofitted tests around untested code, mocked on request without a seam, investigated a live payments incident without ever mitigating it. With the skill loaded, every one of those failures reversed: 12/12 GREEN scenarios, zero forbidden behaviors.
- **A router that earns its overhead.** 16/16 routing accuracy on the full request set, zero fast-path violations across every run — including the negatives (i18n, registry, migration, cross-repo) designed to tempt it into skipping ceremony. When a run disagreed with the answer key, the key was wrong: the router had applied the spec more faithfully than its own test.
- **Reviewed like it reviews you.** Every skill went through fresh-context two-verdict review (spec compliance, then quality). The reviews caught real defects — a project binding hardcoded into a generic skill, an interface mismatch between siblings, a missing file convention — and every fix was re-reviewed to RESOLVED.
- **Lean enough to always be on.** The v0.1 core was 15 skills + bootstrap in 1,934 lines (superpowers spent 3,150 on 14), with a standing context cost of ~1,240 tokens — the bootstrap and one-line triggers are all a session carries until a skill actually fires.
- **An audit trail, not a changelog claim.** Every RED, GREEN, review verdict, and gate lives as a greppable `EV` line in `memory-progress.md`, tied to the commit that produced it.
- **Built by itself.** Releases `0.2` through `0.5` were each shaped, planned, wave-executed, reviewed, and shipped through galdr's own flow, with adversarial review at every gate.

## Install

galdr is a Claude Code plugin.

1. Add the marketplace and install the plugin:
   ```
   /plugin marketplace add nyelonong/galdr        # your GitHub owner/repo, or a local path
   /plugin install galdr@galdr
   ```
2. Enable the always-on core — it ships **disabled**, so you opt in:
   ```
   touch ~/.claude/plugins/cache/galdr/galdr/<version>/hooks/enabled
   ```
3. Wire each repo once: `/galdr:setup` (writes `docs/agents/galdr.md` — gate commands, invariants, model tiers, thresholds, smoke config).
4. Optional, once per machine: `/galdr:usage-bridge install` — real 5h/7d usage % and the quota-threshold park, even where your statusline doesn't already write the cache.

Then just work. The router picks the right path on every substantive request.

## Use

With the hook enabled, the router runs on any substantive request and announces its pick in one line (`routing: <destination> — <reason>`); one word from you overrides it. Every skill is also a slash command (`/galdr:<name>`), so you can enter the flow directly at any point.

- **Direct on-ramps:** `/galdr:debug` (a reported bug — root cause before fix), `/galdr:prototype` (a design question faster answered by a throwaway build than a spec), `/galdr:rearchitect` (architecture pain with no specific feature).
- **Review the backlog:** `/galdr:backlog` lists open deferred work; the deferring skills append to it automatically, and `branches` finish proposes it back to you.
- **Not sure which skill?** `/galdr:using-galdr` tells confusable pairs apart (shape vs prototype, review vs verify, debug vs tdd, plan vs waves).

Skills stay generic; each repo's specifics live in `docs/agents/galdr.md` from `/galdr:setup`.

## Usage bridge

`/galdr:usage-bridge install|uninstall|status` installs a statusline wrapper that writes `~/.claude/rate-limits-cache.json`, so the real 5h/7d usage % and the quota-threshold park work on any machine — not just where the official statusline already populates that cache. It wraps whatever statusline you already have non-destructively (delegating to it after writing the cache) and is fully reversible: `install` sets it up, `uninstall` restores your original statusline, `status` reports which state you're in.
