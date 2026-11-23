# Circuit breaker: failure classification and tuning

This reference applies only when repository evidence shows a circuit breaker or concurrency limit is
needed and no existing transport, service-mesh, or platform layer already owns it. Use the
repository's established implementation. Do not introduce a new dependency or select a library from
this guide.

## Required semantics

A breaker protects callers from a demonstrably unhealthy upstream. It must distinguish:

- an attempted upstream call from a local rejection because the breaker is open;
- an open-breaker rejection from a local concurrency-limit rejection;
- upstream-health failures from expected business outcomes; and
- a local attempt timeout from caller cancellation or expiry of an overall request budget.

One breaker state should normally represent one independently failing upstream dependency. Couple
state only when the dependencies, failure modes, and recovery behavior are intentionally shared.

## Failure classification

Count only evidence that the upstream is unhealthy toward opening a breaker. Typical examples are a
documented server failure, a transport failure that prevented a response, or an attempt deadline
that elapsed while calling the upstream. Do not count expected business outcomes, validation
failures, caller cancellation, or expiry of an overall caller or retry budget.

Status codes alone are insufficient for some decisions. A quota or concurrency response can indicate
a caller-scoped policy, a business conflict, or shared upstream saturation. Classify it from the
upstream's documented reason, scope, and response metadata. Preserve the underlying business error
for the caller even when the breaker excludes it from its failure accounting.

Use the repository's chosen API to inspect structured rejection state or error types. Never identify
an open breaker by matching error strings, and do not assume all implementations expose the same
sentinel or callback shape.

## Tuning

Derive every threshold, rolling window, recovery probe interval, timeout, and concurrency limit
from repository evidence: representative traffic and failure measurements, latency or availability
objectives, upstream limits, and load tests. Existing platform policy takes precedence. Do not copy
illustrative durations, percentages, or request counts into production configuration.

A volume threshold should prevent sparse traffic from turning one failure into a misleading error
rate. Recovery probes should balance avoiding pressure on a still-failing upstream against prompt
recovery. A concurrency limit should bound local resource use under a slow dependency and be
reported as local shedding rather than as an upstream call.

## Wiring checklist

- Confirm the repository has no existing layer that already supplies the control.
- Give each independently failing dependency separate state unless there is documented coupling.
- Propagate a caller-derived, per-attempt context to the actual client.
- Keep the per-attempt timeout distinct from the overall caller or retry budget when classification
  requires that distinction.
- Preserve expected business errors for callers while excluding them from breaker failure accounting.
- Distinguish open-breaker and concurrency-limit rejections in logs and metrics.
- Test the chosen implementation's actual rejection and recovery behavior; do not infer it from a
  generic wrapper or error text.
