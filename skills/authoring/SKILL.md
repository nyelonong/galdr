---
name: authoring
description: Use when writing a new galdr skill, editing an existing one, or running the pack's quarterly prune review.
disable-model-invocation: true
---

# authoring

Applies galdr's own build rules to galdr's own skill work — this file included. Every
change to a `SKILL.md` or a `references/` file in this pack goes through the checks
below before it's written.

## No-op test

Before writing a line, ask: does this line change behavior versus not having it? If a
model already does this by default, the line is a no-op — cut it, don't soften it. Run
this at the sentence level, not just the section level: a file that reads clean can
still hide individual no-op sentences.

## Before writing a discipline skill: capture, don't guess

A discipline skill enforces a rule under pressure (tdd, verify, debug, bootstrap,
route, continue). For these, run the scenario without the skill first, per
`testing/protocol.md` §1, and record the verbatim rationalization under `## Baseline
captures` in the scenario file. Every row in the skill's rationalization table must
trace to a captured excuse. A row invented without a capture is a guess, and a guess
misses the loophole the agent actually reaches for — write the baseline run before the
table, not after.

General skills (reference, orchestrator) skip this step; they go straight to the
spot-check in `testing/protocol.md` §2.

## Match the form to the failure

Two different failures need two different fixes, and each form backfires on the
other's failure:

| Failure | Right form | Why the other form fails |
|---|---|---|
| Skips or breaks a rule under pressure | Prohibition + rationalization table built from captures | A positive recipe leaves the rule negotiable — the agent complies with the letter, not the discipline |
| Output has the wrong shape (bloated, buried, restated) | Positive recipe: state the output's parts, in order | A prohibition ("don't restate") gives the agent something to argue around instead of a shape to fill |

Prohibition tables are for rule-skipping only. Everywhere else, write the positive
recipe.

## Two-loads accounting

Every skill spends two separate budgets:

- **Every session:** the frontmatter `description`, loaded whether the skill fires or
  not. Keep it to trigger conditions.
- **On load:** the skill body, paid only when the skill fires. Detail not needed on
  every branch belongs in a `references/` file — the body stays lean, the reference
  loads only when its pointer fires.

Before adding a paragraph, name which budget it's charged to. If it's the description,
it must be a trigger, not an explanation of mechanics.

## Trigger-only descriptions

The description says when to use the skill, never how it works inside. "Use when
reviewing a branch" is a trigger; "runs two parallel review passes and merges them" is
a mechanics leak — cut it. A description that summarizes the workflow teaches the
agent to act on the summary and skip the body.

## One-level-deep references

A `references/` file may hold detail the body doesn't need on every run. It may not
point to a `references/` file of its own — one hop from `SKILL.md`, no deeper. A
reference file that needs its own reference means the skill is doing too much; split
it instead.

## Completion criterion in every procedure

Every step or procedure this skill's content prescribes states when it's done —
checkable, not "produce a good result." A step with no completion criterion invites
stopping early, because nothing says what "done" looks like. Write the criterion
before the step that leads to it.

## Proportional testing

Test cost matches the skill's kind. `testing/protocol.md` is canonical for both
procedures — the one-line routing rule: discipline skills take the pressure test
(§1: RED baseline, then GREEN with the skill's content pasted inline); every other
skill takes the retrieval spot-check (§2: load the SKILL.md, ask the scenario's probe,
check the answer cites the right section). Everything past that routing lives in
protocol.md alone.

## Line budgets

Check before committing:

```
wc -l skills/<name>/SKILL.md
```

A budget is a ceiling, not a target — don't pad a skill to reach it. Budget growth is
not a rewrite convenience: per spec §12, a discipline skill's budget grows only after
it fails its pressure campaign at the current size, and that failure is the
justification recorded in the commit. Growing a budget with no failed pressure run to
point to is scope creep, not maintenance.

## Quarterly prune ritual

On a quarterly cadence, or whenever the pack feels heavier than it earns:

1. Grep memory-progress.md / session logs for which skills fired this quarter and
   which never did.
2. Re-run the no-op test on skills that haven't changed in a while — models improve,
   and a rule that once changed behavior can go quiet.
3. Deprecate before adding: a skill that stopped earning its load gets removed (or
   folded into using-galdr's map) before a new one is written. Sediment — stale
   content that piled up because adding felt safe and removing felt risky — is the
   default fate of a pack that only ever adds.

The ritual is done when every currently-installed skill has a fired/not-fired verdict
for the quarter and every "not fired" skill has an explicit keep-or-deprecate decision.

## Notes

- User-only: invoked by name, never by the router.
- Applies to every skill in this pack, including edits to this file — an edit to
  authoring.md goes through its own no-op test and budget check first.
