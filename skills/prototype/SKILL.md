---
name: prototype
description: Use when a design question can be answered faster by building working throwaway code than by writing a spec or arguing about it — comparing two implementation approaches, checking how a library or API actually behaves, or testing whether an idea works before committing to a plan. User-invoked only.
disable-model-invocation: true
---

# prototype

Builds throwaway code to answer one named design question. prototype never produces
production code directly — the real implementation still goes through `plan` and `tdd`,
starting from a failing test, after the prototype has answered the question.

## Entry rule

Write the design question down first, one sentence, before writing any code. No named
question, no prototype — if there's nothing to write down, this isn't a design question
worth prototyping, it's just building the feature; route to `shape` or `tdd` instead.

Examples of a real question: "Does this library's streaming API handle backpressure the
way we need?" "Is a recursive or an iterative parser faster on our actual data shape?"

## Pure-core, throwaway-shell split

Split what you build into two parts:

- **Pure core** — the logic the question is actually about. Dependency-free: no
  database, no network client, no framework wiring. This is the part whose behavior
  you're trying to learn, and it's what the answer will be based on.
- **Throwaway shell** — everything around the core needed to run it and observe the
  answer (a CLI entry point, a stub server, hardcoded fixtures). Mark it explicitly as
  throwaway, in a comment or the file name (`shell_throwaway.go`, `main.throwaway.ts`),
  so nobody mistakes it for a real entry point later.

## Variant switcher for comparative questions

When the question compares two or more approaches — not "does X work" but "is X or Y
better" — build every variant behind one switch in the same throwaway build, not as
separate scripts:

- Web UI: a `?variant=a` / `?variant=b` query param that swaps the implementation at
  the same route.
- Go: a `-variant` flag, or a build tag (`//go:build variantA`), selecting between
  implementations from the same entry point.

One switcher beats parallel scripts: the comparison only means something if every
variant runs under identical conditions, and separately-hacked scripts drift apart in
ways that quietly contaminate the answer.

## Regeneration rule

When the design question changes shape — not a tweak, but genuinely a different
question (a new constraint, a different library, a different data shape) — regenerate
the prototype from scratch. Do not patch the existing one forward. A prototype patched
across two different questions ends up answering neither one reliably.

## The Iron Law exemption — bounded

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST does not apply inside a prototype. This
is the one place in galdr where untested code is written on purpose.

The exemption holds only because all three of these stay true:

- Prototype code never merges into the working tree's default branch.
- Prototype code is never adapted into production — not carried forward, not "cleaned
  up a bit and shipped."
- The prototype is deleted (or moved to the graveyard dir) at exit — deletion is what
  keeps "never adapted" true over time; a prototype left in the tree is an invitation.

If either stops being true — someone merges a prototype branch, or reaches for the
prototype's file as a starting point for the real feature — the exemption no longer
applies, and that code needs the Iron Law like anything else: delete it and restart
from a failing test.

## Exit contract

A prototype ends the same way every time, in this order:

1. **Record the answer.** Write a decision line to memory-progress.md, in the format
   from the continue skill: `DECISION [<topic>] <question> → <choice>`. The question
   is the one written down at entry; the choice is what the prototype showed.
2. **Hand off behaviors, not code.** The behaviors the prototype validated become the
   test list for the implementing wave's plan — each behavior proved out becomes one
   test the real implementation must pass. The handoff is that list, not the prototype's
   files.
3. **Delete or graveyard.** Delete the prototype, or move it into a `prototypes/`
   graveyard dir if it's worth keeping as a reference. Either way it does not stay in
   the working tree as active code. Say which one you chose in the decision line.

The real implementation then goes through `plan` and `tdd` from scratch: a failing test
for each handed-off behavior, minimal code to pass it, same as every other feature. The
prototype's code answered the question — it is not where the test-writing starts, and
it is not something to adapt, tidy up, or reuse.
