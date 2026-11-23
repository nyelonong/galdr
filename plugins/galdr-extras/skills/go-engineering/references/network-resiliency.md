# Go Network Call Resiliency

Read this reference only when the task changes or diagnoses network resilience or database
transaction retry. Routine request mapping, response parsing, client wiring, and ordinary SQL work
do not need it.

Before adding application-layer resilience, inspect the actual client, transport, service mesh,
database, upstream, and repository policy for this route. Reuse the established infrastructure;
do not duplicate retries, deadlines, circuit breaking, caching, concurrency limiting, or telemetry
that another layer already owns. Application code still owns end-to-end caller budgets, idempotency,
semantic retry classification, cache semantics, and application-level observability.

## Choose only the needed controls

Possible controls are timeout, circuit breaking, cache, duplicate-work suppression, observability,
and retry. Add only the controls justified by this call's traffic, criticality, failure modes, and
existing infrastructure. A low-volume, non-critical call may need only a timeout. Do not build an
all-purpose wrapper or add controls speculatively.

When multiple controls are justified, state their scope and interaction. For example, a cache lookup
usually precedes an upstream attempt, and duplicate-work suppression may cover a whole retry
lifecycle. But ordering is not universal: choose it from cache semantics, whether followers may
share a result, caller budgets, and the repository's infrastructure. Do not make one caller's
cancellation, deadline, authorization, or tracing context govern unrelated callers.

## Timeout

Use `context.WithTimeout`, propagate the context to the actual client, and distinguish a local
attempt timeout from caller cancellation or expiry of the overall request budget.

```go
attemptCtx, cancel := context.WithTimeout(ctx, attemptTimeout)
defer cancel()

resp, err := doUpstreamCall(attemptCtx)
if err != nil {
	switch {
	case errors.Is(ctx.Err(), context.Canceled):
		// The caller stopped waiting; do not classify this as upstream failure.
	case errors.Is(ctx.Err(), context.DeadlineExceeded):
		// The overall caller budget ended; do not classify this as a local attempt timeout.
	case errors.Is(attemptCtx.Err(), context.DeadlineExceeded):
		// This attempt exceeded its local budget.
	default:
		// Classify from the client and upstream's documented semantics.
	}
}
```

## Circuit breaking and concurrency limits

Add a breaker or concurrency limit only when repository evidence shows it is needed and no existing
layer provides it. Keep separate state for independent upstream dependencies unless their failures
are intentionally coupled. A breaker must distinguish a locally rejected call from an attempted
upstream call; a concurrency limit should be measured as local shedding, not an upstream failure.

Classify only upstream-health failures as breaker failures. Expected business outcomes, validation
failures, caller cancellation, and expiry of an overall caller budget do not count. A per-attempt
timeout may count only when it reflects the upstream attempt rather than the parent budget. Use the
repository's chosen API to preserve business errors without counting them as breaker failures, and
to identify open or concurrency-limited rejections without guessing from error strings.

Derive thresholds, windows, recovery probes, and concurrency limits from observed traffic, failure
tolerance, upstream limits, and availability objectives. Do not copy illustrative values into
production policy.

## Cache

Start with the repository's existing concrete cache and preserve the value's type. Add a narrow
interface at the consuming boundary only when a real second implementation or test substitution
exists; do not introduce a swappable `any`-typed cache merely because implementations may change.

Before caching, define:

- the complete key and tenant or authorization scope;
- acceptable staleness, expiry, invalidation, and capacity policy;
- ownership of mutable cached values and whether callers receive copies;
- whether negative results and partial responses are cacheable;
- whether cache population is best-effort or correctness-critical.

Populate only results approved by that policy. If cache population is best-effort, report or measure
write failures without failing the successful upstream result. If it is correctness-critical, return
the write error with useful context. Never discard a cache-write error without choosing and stating
one of those policies.

## Database calls and transaction retry

Normal database work uses caller context, repository query helpers, and existing transaction
patterns. Do not add circuit breakers, application caches, duplicate-work suppression, or retries
merely because the database connection uses a network.

Retry only errors the database and repository explicitly classify as transient. Replay the complete
transaction from its beginning so reads and writes are evaluated against a fresh snapshot; never
retry one failed statement inside an otherwise continuing transaction. The transaction callback
must be safe to repeat and must not perform hidden external effects such as sending messages,
charging accounts, or calling another service. If those effects are required, use the repository's
approved idempotency or transactional-outbox design rather than hiding a retry around them.

Bound transaction attempts by the caller's deadline, use backoff only when the database guidance
calls for it, and return the final classified error. Test transaction retry with the real isolated
database engine; a mock does not prove isolation, rollback, locking, or serialization behavior.

## Duplicate-work suppression

Use the repository's existing mechanism only when concurrent callers can safely share the same
in-flight operation. Give the shared operation an independent, bounded service-owned context; do
not let the first caller's cancellation or deadline control every follower. Keep caller-specific
authorization, tracing, and identity out of a shared operation unless they are valid for every
follower. A follower may stop waiting when its own context ends while the bounded shared operation
continues. Return copies when a shared result is mutable.

## Observability

For an outbound call, record rate, errors, and duration using the repository's established telemetry
system. Measure duration around real upstream attempts only; record cache hits, open-breaker
rejections, and local concurrency rejections as distinct outcomes without adding them to upstream
latency. Use the repository's names, units, and dimension conventions.

## Retry

Retry only a call that is safe to repeat or protected by documented idempotency. Bound attempts by
both count and the overall caller budget. Classify retryable failures from the upstream's documented
semantics; caller cancellation, validation failures, and completed business outcomes are not
retryable. Use backoff and jitter when evidence shows retries are needed, and ensure waiting stops
when the caller context ends.

## Checklist when writing or reviewing a resilient call

- Does the context reach the actual client, or is the timeout decorative?
- Does each added control solve a demonstrated problem for this call rather than duplicate existing
  infrastructure?
- Are business outcomes, caller cancellation, locally rejected calls, and upstream-health failures
  classified separately?
- If retry exists, is it safe to repeat and bounded by both attempts and the caller budget?
- Can shared work outlive one caller without carrying caller-specific identity or an unbounded
  lifetime?
- Do metrics use bounded dimensions and distinguish cache hits, local rejections, and real upstream
  errors?
