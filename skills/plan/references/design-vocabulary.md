# Design vocabulary

Vocabulary for declaring seams and module boundaries at plan time. Loaded by `plan`
when a task needs to name a seam or a test strategy.

## Deletion test

A module earns its place if deleting it would force its callers to absorb the
complexity it currently hides. If deleting a wrapper just means callers call the
underlying thing directly with one extra line, the wrapper isn't earning its keep —
inline it instead of declaring it as a seam.

## Two-adapter rule

Don't introduce an abstraction (interface, adapter, plugin point) until there are two
real, distinct consumers that need it. One consumer is not evidence of a pattern — it
is speculative generality. Wait for the second real caller, then extract.

## Interface-is-the-test-surface

Whatever a seam's interface exposes is exactly what its tests should exercise. If a
test has to reach past the interface — into a struct's internals, or a mock's internal
call count — the seam is drawn in the wrong place; move it to the boundary the test
actually needs.

## Dependency-category → test-strategy table

| Dependency category | Test strategy |
|---|---|
| Pure logic, no I/O | Unit test; no seam needed |
| Owned database/store | Integration test against a real instance (container or local) |
| External API you don't own | Contract test + fake at the client boundary |
| Time or randomness | Inject the clock/rand source; seam at construction |

Declare which category each task's dependency falls into; the strategy follows
directly from the row.

## Design-it-twice

Before committing to a seam or module boundary, sketch two orthogonal framings (for
example: "split by data type" vs. "split by consumer") — one paragraph each — then pick
one and say why in one line. Skipping this step is how the first idea that comes to
mind gets built, untested against alternatives.

## Go notes

- **Implicit interfaces**: define the interface on the consumer side, next to the code
  that uses it — not next to the implementation. The implementation doesn't need to
  know an interface exists.
- **Accept interfaces, return structs**: constructors return concrete types; function
  parameters accept the narrowest interface that does the job, not the concrete type.

## TS notes

- **Branded ids at seams**: cross a seam boundary with a branded type (for example
  `type UserId = string & { __brand: 'UserId' }`), never a bare `string` or `number`. A
  mismatched id then fails to typecheck instead of failing silently at runtime.
