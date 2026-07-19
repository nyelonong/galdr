---
name: shape
description: Use when turning a fuzzy idea, a position to stress-test, or a set of already-clear requirements into a written spec — grill mode tests a position, explore mode is open-ended, synthesis mode drafts straight from clear requirements. Invoke via route or explicit command.
---

# shape

Turns an idea into a spec file. Three entry modes reach the same exit: a written
spec, self-reviewed, waiting on approval. Route hands you a mode directly
(`shape-synthesis`, `shape-grill`, `shape-explore`, `shape-wayfinder`); a request
that names a mode itself — "grill me", "requirements are settled" — picks the mode
the same way.

## Picking a mode, if not already told

- A position exists and needs stress-testing → grill.
- Open-ended, no position yet → explore.
- Requirements are already clear enough to state → synthesis.
- The topic won't resolve in one sitting → wayfinder (below).

## Grill

Stress-tests a position someone already holds.

1. Build a decision tree of the open questions, ordered by dependency: which
   decisions block which others. An early answer can change what the later
   questions even are.
2. Split each node into a fact or a decision. A fact is checkable — confirm it
   (read the code, ask one direct question) and move on. A decision is a choice
   among options — that gets the interview treatment below.
3. Ask one decision at a time, in dependency order. Never put a list of questions
   in one turn — the position gets stress-tested one decision at a time.
4. Every question carries a concrete recommendation: state your pick and the
   one-line reason before asking, then let the user confirm, override, or answer
   differently. A bare question with no stance is not a grill question.

   ```
   Next: does "reviews" mean buyer reviews of a storefront, or reviews of the
   platform itself? Recommend buyer reviews of a storefront — that's the noun
   already in use, and "platform reviews" isn't a stated need yet.
   ```

5. The moment a decision confirms, append its line to memory-progress.md —
   immediately, not batched for later. An interview is exactly the kind of work a
   session dies mid-way through; a decision that only lives in the conversation
   dies with it.

   ```
   DECISION [<topic>] <question> → <choice>
   ```

6. Keep going until every branch of the tree is resolved or explicitly deferred
   with a named owner. "This got hard, let's stop" is not an exit — resolved or
   deferred-with-an-owner are the only two ways out of grill. When you defer a
   branch to a later cycle, append it to the backlog per /galdr:backlog
   (skills/backlog/SKILL.md) — don't restate the format here.
7. Once the tree is exhausted, continue to Synthesis.

## Explore

Open-ended: no position exists yet to test.

1. Read the project's context first — CLAUDE.md, memory.md, the existing code —
   before proposing anything. An approach that ignores what's already there gets
   rejected on the first read anyway.
2. If the request spans more than one subsystem, decompose the scope: name each
   subsystem's slice of the question separately before designing any of them.
3. For each slice, present 2-3 approaches with a recommendation stated first, not
   a neutral list, before going into design detail: the pick and why, then the
   alternatives and their tradeoffs.
4. Once a direction is picked for a slice, any open question left in it gets the
   same treatment as grill: one at a time, recommendation first.
5. Continue to Synthesis.

## Synthesis

The exit every mode reaches, and a mode in its own right.

- Entered directly (`shape-synthesis`, or the requirements are already stated as
  clear): skip the interview entirely. Do not ask a clarifying question — the
  request already said what's needed. Go straight to the spec draft.
- Arrived here after grill or explore: the interview already happened; there is
  nothing left to skip, just write.

Write the spec to `docs/specs/YYYY-MM-DD-<topic>.md` in the target repo. Near the
header, carry a one-line `Lifecycle status:` field. It moves through four states
over the spec's life — `shaped → planned → in-progress → shipped` — and shape
sets it to `shaped` when it writes the spec.

- **Goal** — what this spec is for, one paragraph.
- **Non-goals** — what's explicitly out of scope, so it can't drift back in later.
- **Constraints** — project-wide rules every task must obey (style, consent,
  cross-repo invariants). The plan skill copies this section forward verbatim, so
  write it as rules, not prose.
- **Decision log** — every decision reached (grill/explore) or assumed (direct
  synthesis), as a table: `# | Decision | Choice`.
- **Acceptance criteria** — stated per future wave, so the downstream `plan` skill
  has something concrete to check tasks against.

### 4-point self-review

Before showing the spec, check it against these four and fix inline — don't flag
a problem and leave it for later:

1. **Placeholders** — any "TBD", "handle edge cases", "similar to X"? Replace with
   the actual content.
2. **Contradictions** — do any two sections disagree with each other? Reconcile
   them.
3. **Scope** — does the spec match what was actually asked, no more and no less?
   Trim anything that crept in.
4. **Ambiguity** — could two different readers build this two different ways?
   Sharpen the wording until one reading survives.

### Hard gate

No implementation action — no code, no plan file, no wave dispatch — happens
until the user has approved this spec. This is a hard rule, not a preference: an
unapproved spec is a draft, and drafts don't get built.

## Wayfinder

When a topic won't reach a spec in one session — too many open branches, or the
session runs out before the tree is exhausted — load `references/wayfinder.md`.
It covers the multi-session fog map: what to record, what never to record, and
how the map closes back out into a spec.

## Notes

- A memory-progress.md decision line and the spec's Decision log table are not
  the same artifact: the line is written the moment a decision lands, mid-
  interview; the table is the same decisions, collected, at the end.
- Facts and decisions differ in treatment, not in stakes — a wrongly assumed fact
  is still a spec bug, it just didn't need an interview to catch.
