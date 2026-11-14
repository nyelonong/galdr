---
name: shape
description: Use when the user runs /galdr:shape to turn a fuzzy idea, a position to stress-test, or settled requirements into the goal and decisions of a plan.
disable-model-invocation: true
---

# shape

Writes the what and why of an idea as the top half of its plan file,
`docs/plans/<YYYY-MM-DD>-<topic>.md`.

## Pick a mode

- Requirements already settled → **synthesis**: no questions, write the plan's top half.
- A position to stress-test ("grill me") → **grill**.
- No position yet → **explore**.

## Settle facts by trying, not asking

Before each question, check whether reading the code, docs or config, or running
something, answers it. Such a fact goes into the plan with its source; it is never
asked. Only decisions, choices among options that change what gets built, reach the
user.

## Question budget

- One question per message, never a list.
- Recommendation first: your pick and its one-line reason, then the question.

  ```
  Next: do "reviews" mean buyer reviews of a storefront, or reviews of the platform?
  Recommend buyer reviews of a storefront: that noun is already in use, and platform
  reviews are not a stated need.
  ```

- Synthesis and explore ask at most 3 questions before the draft. Every decision still
  open goes into the plan as an assumption carrying your recommended choice.
- Grill was asked for questions: keep going, one at a time, until the tree is resolved
  or the user stops.
- Default to the simplest design that meets the stated need. A heavier option (queue,
  outbox, new service, new abstraction) appears only as a rejected alternative with its
  reason, unless the user asked for it.

## Grill

1. List the open decisions as a tree ordered by dependency: an early answer can change
   the later questions.
2. Ask them in that order, under the budget above.
3. Write each confirmed decision into the plan's Decisions table as it lands,
   creating the file at the first one, so a session that dies loses nothing.
4. Done when every branch is decided or deferred with a named owner. Then synthesis.

## Explore

1. Read the project's instructions and the existing code before proposing anything.
2. If the request spans several subsystems, name each one's slice before designing any.
3. For each slice, give 2 or 3 approaches, recommendation first, then the trade-offs.
4. Open questions left in a slice follow the budget. Then synthesis.

## Synthesis

Write the plan's top half in the format of `skills/galdr/references/plan-format.md`:
title, status line (`draft · next: /galdr`), header, Goal, Out of scope, Done when, and
Decisions with each choice's why, trade-off and source. Add Design only when the
discussion settled it.

Then fix inline, before showing it:

1. Placeholders: no "TBD", "handle edge cases" or "similar to X".
2. Contradictions between sections.
3. Scope: no more and no less than was asked.
4. Ambiguity: if two readers could build it two ways, sharpen it.

## End

shape writes no tasks and no code. End with "Next: run `/galdr` to add the tasks; you
approve the whole plan once, before any code."

Done when the plan file has these sections and passes the four checks.
