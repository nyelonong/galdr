# Observability: outbound-call outcomes and dimensions

This is the detail for outbound-call observability. Use the
repository's established telemetry system and naming conventions. The required outcomes are
provider-neutral: make rate, errors, duration, and the reason for each outcome visible without
introducing a new provider or telemetry library.

## Measurements

For an outbound call, record:

- a count of logical outcomes, including cache hits and locally rejected calls;
- duration of real upstream attempts only; and
- in-flight work only when the repository uses and can act on that measure.

Use the repository's metric names and units. Choose duration units and histogram boundaries from
its existing conventions and the relevant service objective; do not copy generic bucket values.

## Dimensions

Attach only bounded dimensions needed to identify the caller, upstream, operation, use case, and
outcome. Reuse repository conventions for keys and values. A practical set may include:

| Dimension | Example purpose |
|---|---|
| upstream | identify the dependency |
| operation | identify the RPC, method, or templated route |
| use case | identify the bounded business action |
| outcome | identify the result taxonomy below |

Every distinct dimension combination creates a separate time series. Never use unbounded values
such as user IDs, raw URLs with path parameters, full error messages, or request IDs. Put necessary
high-cardinality detail in the repository's trace or log mechanism instead of a metric.

## Outcome taxonomy

Use a bounded taxonomy aligned with the repository's client and breaker semantics. The exact names
are repository-owned, but distinguish at least:

| Outcome | Meaning |
|---|---|
| success | the upstream operation succeeded |
| expected business outcome | the upstream responded with an expected non-success result |
| local attempt timeout | this operation's own attempt deadline elapsed |
| caller or overall budget deadline | a caller or broader budget ended without proving the upstream was unhealthy |
| canceled | the caller canceled the work |
| upstream failure | a transport or documented server-side failure |
| breaker open | a breaker rejected the call before an upstream attempt |
| concurrency limited | a local limit rejected the call before an upstream attempt |
| cache hit | a cached value served the request |

Do not collapse local timeout, caller cancellation, cache hits, breaker rejections, and upstream
failures into one generic error. The repository may combine or further split these outcomes when its
operational policy documents why.

## Recording boundaries

Count every logical outcome. Record duration from immediately before the real upstream attempt to
immediately after it returns. Do not add a cache hit, open-breaker rejection, or local concurrency
rejection to the upstream-latency distribution; record its count under its own outcome instead.

When a call includes retries, decide and document whether measurements represent attempts, logical
requests, or both. Keep that meaning consistent with existing dashboards and alerts. Do not infer
an upstream attempt from a locally rejected call.

## Traces, logs, and exemplars

Use the repository's existing trace and log integration for request-specific or high-cardinality
detail. Keep the same bounded operation and outcome dimensions where that helps correlate signals,
but follow the repository's privacy and retention policy. If the installed telemetry system supports
links from latency measurements to traces, use it only when it is already configured and useful for
operational diagnosis.

## Verification checklist

- Does the implementation use the repository's existing telemetry integration and conventions?
- Are metric dimensions bounded and free of sensitive or unbounded identifiers?
- Are cache hits and locally rejected calls counted but excluded from upstream latency?
- Can an operator distinguish expected business outcomes, cancellations, deadline classes, and
  upstream failures?
- Is the measurement scope (attempt, logical request, or both) clear and consistent?
