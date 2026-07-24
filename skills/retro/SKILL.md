---
name: retro
description: Use when reading the evidence ledger back in aggregate — at or after a release close, or on user request. Never runs automatically; a proposal surfaced elsewhere or a direct user ask are the only triggers.
disable-model-invocation: true
---

# retro

Reads `memory-progress.md` and `memory-progress-archive.md` back in aggregate, across
one or more closed cycles, and reports five metric families. retro is read-only: it
writes no files, changes no config, and applies no proposal on its own.

## Cycle boundaries

A cycle is the span between two `CLOSEOUT` or `RELEASED` markers (either marker closes a
cycle; the two are not distinguished for aggregation). Read both ledger files always —
`memory-progress.md` holds the current cycle, `memory-progress-archive.md` holds
rotated-out history — and split each file's lines into cycles at those markers before
computing any metric. "The last cycle" means the span since the most recent marker; a
request naming an earlier point (e.g. "since 0.9") starts the span there instead.

## The five metric families

Run all five, every time, against both files. A family with zero hits is reported as
zero, never skipped or omitted from the report.

1. **Tier escalations.** `grep -h 'attempt=' memory-progress.md memory-progress-archive.md`.
   Count attempts beyond 1 (`attempt=1` is a first try, not an escalation) and the rung
   distribution (which tier each escalation moved to). Sample:
   `EV [spec-review] crash-recovery spec attempt=2 top@max → fixes-needed: ...`. No live
   multi-attempt instance may exist yet in a young ledger — that is itself a reportable
   zero, per the 0.9.0 decision line: "failed attempts and escalations each write an EV
   line with attempt=N and tier@effort".
2. **Review verdicts.** `grep -h 'PASS WITH NOTES\|axis → PASS\|axis → FAIL' memory-progress.md memory-progress-archive.md`.
   Distribution across cycles, per axis (Standards, Spec): PASS / PASS WITH NOTES / FAIL.
   Sample: `EV [review] Standards axis → PASS WITH NOTES: S1 CLAUDE.md stale gate wording
   (Minor, fixed @d1862d2)`.
3. **Trust gap.** `grep -h 'return reviewed status=' memory-progress.md memory-progress-archive.md`.
   Count returns whose reviewed status differs from `complete` (needs-decision, failed,
   downgraded) against the total returns seen. Sample:
   `EV [waves] 2.1 return reviewed status=needs-decision @e08afa8`.
4. **Interruptions.** `grep -h '^PARKED\|^CRASH\|LOST-RISK' memory-progress.md memory-progress-archive.md`.
   Count parks, crashes, and lost-risk markers. Formats per continue §6/§9: `PARKED
   <date> — hard: <reason>`, a `CRASH` marker, `LOST-RISK <task-id> …`. No live instance
   may exist yet — report the zero rather than skipping the family.
5. **Spend.** `grep -h 'usage — tokens' memory-progress.md memory-progress-archive.md`.
   Tokens per wave, summed per cycle. Sample:
   `EV [wave-1/gate] usage — tokens 136599 cum 136599; 5h 46% 7d 67% @a85bb08`.

## Report shape

Aggregate each family per cycle first (using the CLOSEOUT/RELEASED boundaries above),
then roll the per-cycle numbers up across every cycle read. Name outliers explicitly — a
cycle whose escalation count, spend, or trust gap sits well outside the others gets
called out by name, not buried inside an average.

## Proposals

Propose at most 3 tunings, recommendation-first: the strongest recommendation stated
first, never a neutral list of equal options. Each proposal names the exact thing it
would change: a `docs/agents/galdr.md` §Models tier→(model, effort) binding, a
`## Budget` threshold line, a §Line budgets row, or a backlog entry written in
`skills/backlog/SKILL.md`'s entry format (what / why / target / source). A proposal with
no concrete target line to name is not ready to propose — sharpen it or drop it.

## Closing line

Every retro report ends with an explicit line: retro applied nothing to the repo or its
config; any accepted proposal goes through the normal consent flow (the same
per-action authorization every other config or file change in this pack requires), not
through retro itself.
