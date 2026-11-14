---
name: shape
description: Use when the user runs /galdr:shape to turn a fuzzy idea, a position to stress-test, or settled requirements into a written spec.
disable-model-invocation: true
---

# shape

Turns an idea into an approved spec at `docs/specs/<YYYY-MM-DD>-<topic>.md`.

## Pick a mode

- Requirements already settled → **synthesis**: no questions, write the spec.
- A position to stress-test ("grill me") → **grill**.
- No position yet → **explore**.

## Settle facts by trying, not asking

Before each question, check whether reading the code, docs or config, or running
something, answers it. Such a fact goes into the spec with its source; it is never
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
  open goes into the spec as an assumption carrying your recommended choice.
- Grill was asked for questions: keep going, one at a time, until the tree is resolved
  or the user stops.
- Default to the simplest design that meets the stated need. A heavier option (queue,
  outbox, new service, new abstraction) appears only as a rejected alternative with its
  reason, unless the user asked for it.

## Grill

1. List the open decisions as a tree ordered by dependency: an early answer can change
   the later questions.
2. Ask them in that order, under the budget above.
3. Write each confirmed decision into the spec's decision table as it lands, creating
   the file at the first one, so a session that dies loses nothing.
4. Done when every branch is decided or deferred with a named owner. Then synthesis.

## Explore

1. Read the project's instructions and the existing code before proposing anything.
2. If the request spans several subsystems, name each one's slice before designing any.
3. For each slice, give 2 or 3 approaches, recommendation first, then the trade-offs.
4. Open questions left in a slice follow the budget. Then synthesis.

## Synthesis

Write the spec with these sections, in order:

- **Goal**: one paragraph.
- **Non-goals**: what is out of scope.
- **Constraints**: rules every task must obey, written as rules.
- **Decisions**: table `# | Decision | Choice | Source`, where Source is `asked`,
  `found` (with where) or `assumed`.
- **Acceptance criteria**: each decidable by a command or an observable check.

Then fix inline, before showing it:

1. Placeholders: no "TBD", "handle edge cases" or "similar to X".
2. Contradictions between sections.
3. Scope: no more and no less than was asked.
4. Ambiguity: if two readers could build it two ways, sharpen it until one reading is
   left.

## Hard gate

No code, plan file or task starts until the user approves the spec. On approval, end
with "Next: run `/galdr` to build it with the feature playbook."

Done when the spec file exists, passes the four checks, and the user has approved it.
