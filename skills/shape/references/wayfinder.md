# Wayfinder

For when a topic can't reach a spec in one session: too many open branches, or
the session runs out before grill's tree (or explore's scope) is exhausted.
Multi-session fog needs an index that survives the gap, not just memory.

## The map

Create `memory-map-<topic>.md` beside memory.md, in the target repo. It is an
index of decisions, never their content — no research notes, no reasoning
paragraphs, no draft spec text. Just enough per node to know its status and
resume the thread.

Each node is one of two states:

- **fog** — unresolved. One line naming the open question and what it depends on.
- **cleared** — decided. One line: the choice, plus a one-line ADR (the reason,
  compressed to a sentence).

```
## <topic>

- [fog] does "reviews" mean buyer reviews or platform reviews? — blocks: scope line
- [cleared] scope = storefronts only, not the platform → storefront is the
  product noun already in use; platform reviews aren't a stated need
```

A cleared node's decision was already written to memory-progress.md the moment
it landed (grill's rule); the map just indexes it for a future session that
doesn't want to re-read the whole file.

## Fog-or-ticket test

Apply this to every node before ending a session: is this genuinely fog — an
open question this spec cannot ship without answering — or is it actually a
ticket, separate follow-up work that doesn't block the spec? A node that's
answerable right now with what's already known is not fog; clear it. A node
that's real but doesn't gate this spec is not fog either; it's scope creep —
move it out, don't leave it in the map marked as something blocking progress.

## Exit contract

- **Map fully cleared** → emit the spec via shape's synthesis mode: every
  decision is already recorded, so synthesis skips the interview and drafts
  straight from the map plus memory-progress.md.
- **Map abandoned** → write one rejection line in the project's backlog doc,
  under that repo's existing deferral rule. Don't leave the topic undecided
  with no written record — a written rejection is what stops it resurfacing
  next session.
