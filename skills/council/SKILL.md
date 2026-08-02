---
name: council
description: Use when the user runs /galdr:council on a hard design question that needs several independent positions and their surviving disagreements, not one answer. Slash-command only, not router- or model-invoked.
disable-model-invocation: true
---

# council

council is a consult, not an executor. Four members answer one question in parallel,
each through its own lens, blind to each other. Then all four run again, each holding
every round-1 answer, each critiquing the other three and either revising or holding.
The main session synthesizes. Nothing is written to disk except one ledger line.

## Write the question first

Write the problem down as one question before any dispatch. If it will not compress to
one question, it is not ready for a council yet.

Then check the three redirects:

- A defect report ("it crashes on this input", "this test is flaky") goes to `debug`.
- A request to judge an existing diff, branch, or PR goes to `review`.
- A question with a single factual answer that reading the code would settle gets
  answered directly, right now.

Anything else proceeds. A council is for a question where competent engineers would
disagree, and seeing where they disagree is worth more than one confident answer.

## The four members

| Member | Lens | Stated bias |
|---|---|---|
| The Architect | Long-term structure: how the choice constrains the system a year out, what it couples, what it makes impossible later | Over-generalizes, builds structure the problem does not need yet |
| The Skeptic | Failure modes: what breaks, which assumptions carry no evidence, what the happy path hides | Risk-averse, can argue you out of work worth doing |
| The Pragmatist | Cost and delivery: the smallest change that solves the real problem now, what defers safely, what it costs to maintain | Under-invests in structure, accumulates debt |
| The Researcher | Evidence and prior art: what the code, the docs, or the library actually do rather than what everyone assumes | Supplies facts without committing to a position |

The bias is written down because it is handed to the other three in round 2. A critique
then has a specific target ("that is the over-generalization again, here is where"),
instead of a general objection nobody can act on.

**Substitution.** Swap or add a member by naming it in the request, for example a
Security member or an Operator member. A substituted or added member needs a written
lens and a stated bias before dispatch, the same two columns as the four above.

## Tools and model tier

- Every member: read and search over the repo, and nothing that mutates. No write, no
  edit, no shell mutation, no commit, no push, no ledger append.
- The Researcher additionally gets web search and documentation lookup.
- Substituted and added members inherit the same grants.
- All eight dispatches resolve the `council` activity row in the repo's
  `docs/agents/galdr.md` §Models. A repo with no `council` row runs them at the session
  model.

## Round 1

Four dispatches in parallel. Each one gets:

- the question exactly as written,
- the repo it may read,
- its own lens and its own stated bias,
- nothing about the other three members.

Each returns a position, the reasoning behind it, and the specific files or sources it
relied on.

## Round 2

Four dispatches in parallel again. Each one gets all four round-1 answers and all four
stated biases. Each returns:

- one critique per other member, each pointing at a named claim in that member's answer
  rather than a general impression,
- either a revised position, or the literal `position unchanged` plus why the critiques
  did not move it.

Holding a position is a valid return. Holding it without saying why is not.

## Synthesis

The main session writes the synthesis, never a fifth agent and never one of the members.
Three parts, in this order:

1. One recommendation, and the reason it wins.
2. Every disagreement that survived round 2: who holds it, and what evidence would
   settle it.
3. Anything all four members assumed without checking.

**Partial returns.** If a dispatch fails or comes back empty, name the missing member,
synthesize from the rest, and say plainly that the council ran short. Do not back-fill
the missing position: writing it yourself replaces an independent answer with your own.

## Dispatch mechanism, or stop

Check for a parallel dispatch mechanism before round 1. The per-runtime mechanism is in
`skills/waves/references/runtime-dispatch.md`; read it there rather than assuming one.

If no mechanism exists, report that and stop. Do not write the four personas yourself.
A single context writing four personas is not a council: independence is the whole
product, and a simulated one looks identical while carrying none of it.

## Ledger

After synthesis, the main session appends exactly one line to `memory-progress.md`:

```
COUNCIL [<topic>] <question> → <recommendation> (dissent: <member> | none)
```

One line per run, and nothing else on disk. No spec, no plan, no branch, no code.
