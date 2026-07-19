---
name: rearchitect
description: Use when architecture pain is blocking current work, or for a periodic pass over a known pain area — maps the area read-only, ranks findings, stress-tests the top one, and exits into a plan. Not a standing background activity. User-invoked only.
disable-model-invocation: true
---

# rearchitect

Turns architecture pain into one planned wave, plus a durable record of everything else
that was found and deliberately not done yet. rearchitect never edits production code
itself — it explores, ranks, stress-tests one finding, and hands the confirmed result to
`plan`.

## Cadence

Run this when architecture pain is actually blocking the task in front of you, or as a
periodic pass over one named pain area. Do not run it speculatively with no pain area
named, and do not treat it as something that runs continuously in the background —
it is a bounded pass with a start and an end, not a monitor.

## 1. Explore — read-only

Dispatch read-only agents (no write tools) over the pain area. Each agent maps, it does
not fix: no edits, no "while I'm here" cleanups, just findings. For each finding, record
one line: what it is, where (file/module), and why it hurts. Use the deletion test from
`skills/plan/references/design-vocabulary.md` as one lens — if deleting a piece and inlining its
callers would be trivial, that piece is exactly the kind of finding worth surfacing.

## 2. Triage — rank, don't just list

Put every finding into exactly one bucket:

- **Blocking-current-work** — stops or slows the task actually in front of you today.
- **Compounding** — not blocking today, but the cost grows every time this area is
  touched again.
- **Cosmetic** — a preference with no measurable cost.

Only blocking and compounding findings are wave candidates. Cosmetic findings never earn
their own wave — file them under rejection memory (below) unless a wave already touching
that exact file picks one up for free.

The top finding is the highest-ranked blocking finding, or if none is blocking, the
costliest compounding one.

## 3. Grill the top finding

Take the top finding into shape's grill mode, treating "is this worth a wave?" as the
position under test. Follow shape's grill mechanics as written: build the dependency-
ordered decision tree, ask one decision at a time with a recommendation stated first,
log each decision to memory-progress.md the moment it lands, and keep going until the
tree is resolved or explicitly deferred with a named owner.

Grill only the top finding in this pass. A pass that tries to grill several findings at
once is not triaging — it is skipping the ranking step above.

## 4. Vocabulary lockdown

If the grilled finding involves renaming a domain concept, agree the new name in
memory.md's `## Domain terms` section — using the `_Avoid_:` alias-pinning format
already used there — before any code is renamed. Renaming code first and reconciling the
glossary afterward is how the drift that section exists to prevent gets in anyway.

## 5. Exit into a plan

Once the grill confirms the finding is worth a wave, hand it to `plan` as that skill's
input: the grilled problem statement plus its resolved decisions stand in for a full
shape spec here — grill already produced the equivalent of a decision log. For any move
wide enough to touch more than one call site or more than one repo, the plan must use
expand-migrate-contract (expand the new path alongside the old, migrate callers one at a
time behind their own tests, contract by deleting the old path once a grep proves zero
callers remain) rather than one rewrite wave.

## 6. Rejection memory

Every finding not taken forward — the rest of what explore surfaced, and anything the
grill itself talks you out of — gets exactly one line in the project's backlog doc,
filed under whatever deferral convention that doc already uses (for example, a "fix now
vs waits for backlog item X" rule). Record what was found, why it was deferred, and
where it lives.

Before an explore pass reports a finding as new, check the backlog doc first. A finding
already filed there is not a fresh discovery — say it's already tracked and move on,
rather than re-litigating it. This is the entire point of rejection memory: dismissed
ideas stop resurfacing every time someone runs explore again.

## 7. Scope guard

Only the wave the plan produced gets built. An improvement noticed mid-wave — even a
small, obviously-correct one — does not get folded in on the spot. Write it as a new
backlog line under the same convention and keep going on the planned task. Small
unplanned edits are exactly how a bounded refactor wave turns into an unbounded one; the
guard applies precisely because the fix looks trivial, not despite it.
