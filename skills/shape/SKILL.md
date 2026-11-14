---
name: shape
description: Use when the user runs /galdr:shape to turn an idea, a position to test, or clear requirements into the goal and decisions of a plan.
disable-model-invocation: true
---

# shape

shape writes the what and the why of an idea. It writes them as the top half of the plan
file, `docs/plans/<YYYY-MM-DD>-<topic>.md`.

## Select a mode

- The user has clear requirements: use **synthesis**. Ask no questions. Write the top half.
- The user has a position to test ("grill me"): use **grill**.
- The user has no position yet: use **explore**.

## Find facts yourself

Before each question, find out if the code, docs, config or a command can answer it.
Write such a fact into the plan with its source. Never ask the user for it. Ask the user
only about decisions: choices that change the result.

## Question budget

- Ask one question in each message. Never ask a list.
- Give your recommendation first, with a one-line reason. Then ask the question.

  ```
  Next: do "reviews" mean buyer reviews of a storefront, or reviews of the platform?
  Recommend buyer reviews of a storefront. That noun is already in use, and nobody
  asked for platform reviews.
  ```

- In synthesis and explore, ask at most 3 questions before the draft. Each open decision
  goes into the plan as an assumption with your recommended choice.
- In grill, the user asked for questions. Continue one at a time until the tree has no
  open branch, or until the user stops.
- Prefer the simplest design that meets the stated need. Show a heavier option (queue,
  outbox, new service, new abstraction) only as a rejected alternative with its reason,
  unless the user asked for it.

## Grill

1. List the open decisions as a tree in order of dependency. An early answer can change
   the later questions.
2. Ask them in that order, within the budget.
3. Write each decision that the user accepts into the Decisions table immediately. Make
   the file at the first decision. Then a session that stops loses nothing.
4. The grill is complete when each branch has a decision, or an owner for a later
   decision. Then do synthesis.

## Explore

1. Read the instructions of the project and the existing code before you propose
   anything.
2. If the request covers many subsystems, name the part for each subsystem before you
   design any part.
3. For each part, give 2 or 3 approaches. Give your recommendation first, then the
   trade-offs.
4. For an uncertain design with a durable effect, one read-only architect subagent can
   give advice. The decision stays with you and the user.
5. Open questions in a part follow the budget. Then do synthesis.

## Synthesis

Write the top half of the plan in the format of `skills/galdr/references/plan-format.md`.
Write these sections:

- the title and the status line (`draft · next: /galdr`)
- the header
- Goal, Out of scope and Done when
- Decisions, with the reason, trade-off and source of each choice

Add Design only when the discussion settled it. Then examine the draft and fix these
problems before you show it:

1. Placeholders: "TBD", "handle edge cases" or "similar to X".
2. Contradictions between sections.
3. Scope: more or less than the user asked for.
4. Ambiguity: two readers can build it in two ways. Make it exact.

## End

shape writes no tasks and no code. End with "Next: run `/galdr` to add the tasks. You
approve the whole plan once, before any code."

shape is complete when the plan file has these sections and passes the four checks.
