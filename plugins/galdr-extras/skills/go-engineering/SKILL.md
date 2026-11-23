---
name: go-engineering
description: Use for Go design, implementation, review, debugging, and refactoring. Establishes a compact evidence-led baseline and points to detailed references only when a focused concern dominates.
---

# Go Engineering

Use current repository evidence and scale inspection to the change. Reuse earlier reads while available and current; refresh affected facts after relevant file changes, context loss, or uncertainty. Inspect applicable `go.mod`, project instructions, code, tests, and CI requirements, rather than rereading every source for a routine fix. Respect the module's declared Go version, build tags, platforms, and existing dependency policy.

## Design

- Prefer obvious code over clever code; it should be understood in one read.
- Prefer clear, idiomatic Go and the standard library.
- Accept small local duplication when it is genuinely simpler and the copies evolve independently; share one common invariant when sharing improves clarity or consistency.
- Avoid decorative reflection and generics when explicit code is clearer.
- Start with concrete types and explicit constructor wiring. A narrow consuming interface may serve demonstrated clarity, maintenance, dependency isolation or meaningful behavioral testing even with one production implementation. Testing current behavior and isolating actual effects are current needs. Do not add it solely to mock calls or anticipate future implementations.
- Keep a switch or if-chain when the case set is closed, small, and dispatched in one place; use a table or map when branches are uniform.
- Extract a polymorphic seam when repeated dispatch, independently growing behavior or state, real substitution, or an approved extension requirement justifies it. Keep the seam at the consuming boundary; implementation count alone does not justify or disqualify it.
- Keep exported APIs small. Treat them as compatibility commitments.
- Comments explain non-obvious constraints or intent, not code mechanics. Prefer clear names and structure; document exported APIs when their contract is not obvious.
- Add dependencies only when their value exceeds their maintenance, licensing, security, and transitive cost.
- Do not add abstraction, concurrency, caching, or a framework without a concrete need.
- For telemetry and resilience, use the repository's established tooling and infrastructure. Do not select or add a provider or library by default; require repository evidence of need and explicit approval.

## Correctness

- Return expected failures as errors; reserve panic for violated programmer invariants.
- Add useful context with `%w` when callers need to inspect the cause. Use `errors.Is` and `errors.As` across error chains.
- Keep technical diagnostics separate from user-facing errors. Do not log the same returned error at every layer.
- Pass `context.Context` as the first argument for blocking or request-scoped work. Propagate it; never replace it with `context.Background()` mid-request. Always call the cancellation function returned by cancellable context constructors.
- Make ownership explicit. Clone slices or maps only when callers must not share mutable state.
- Close resources promptly and check errors that affect correctness, including iterator, flush, and close errors.
- Intentionally ignored errors need an evidenced reason why ignoring them is safe. Prefer clear code; keep a nearby rationale when the reason is non-obvious. A rationale does not excuse a correctness or resource-lifetime failure.

## Concurrency

Use synchronous code until concurrency has a demonstrated benefit. Every goroutine needs an identified owner, exit/cancellation, waiter, error path, channel owner and work/memory bounds. Reuse service shutdown or request completion mechanisms; durability is a separate requirement. Do not hold locks across blocking I/O.

Read `references/concurrency-and-context.md` only when the task adds, changes, reviews, or diagnoses goroutines, channels, synchronization, worker pools, or nontrivial context lifetimes. Routine context propagation and synchronous code do not require that reference.

## Outbound and database calls

Preserve caller cancellation and end-to-end budgets. Ordinary database calls follow the repository's query and transaction patterns. Before adding retries, circuit breakers, caching, singleflight, or new telemetry, inspect the existing client, transport, service-mesh, database, and repository policy so application code does not duplicate infrastructure. Retry only operations that are safe to repeat or protected by documented idempotency.

Read `references/network-resiliency.md` only when the task adds, changes, reviews, or diagnoses timeout budgets, retry or backoff, circuit breaking, caching, singleflight, upstream-failure classification, database transaction retry, or outbound-call observability. Routine request mapping, response parsing, client wiring, and ordinary SQL or database edits do not require that reference.

Also read `references/circuit-breaker.md` when the task adds, changes, reviews, or diagnoses a circuit breaker, and `references/observability.md` when it adds, changes, reviews, or diagnoses metrics, traces, or logs for outbound calls.

## Diagnostics and performance

Read `references/diagnostics-and-benchmarking.md` only when the task diagnoses a hang, race, goroutine leak, CPU or memory problem, latency regression, or makes a performance claim. Routine compiler errors and ordinary focused test failures do not require that reference.

## Change and validation

Test observable behavior at a public or meaningful boundary, not private implementation or collaborator calls. Unit tests run in one process with no network, real time, Docker, or real databases; keep integration tests separate and isolated. Use an isolated real database for database behavior.

After Go changes, format changed files, run `go vet` on affected packages, and run focused tests. Broaden validation by risk:

- concurrent changes: `go test -race` for affected packages;
- dependency or security-boundary changes: when the dependency graph changes, run the repository's module-maintenance command (`go mod tidy` when appropriate), inspect `go.mod` and `go.sum` for unrelated drift, and run the repository's vulnerability checks;
- performance changes: benchmark before and after; do not claim improvement without measurement;
- shared API or refactor changes: inspect callers and implementations, then run the repository's broader test and static-analysis gates.

Use the repository's documented commands and CI requirements when they are stricter.
