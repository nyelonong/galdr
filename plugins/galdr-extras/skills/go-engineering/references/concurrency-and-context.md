# Go Concurrency and Context

Read this reference only when the task adds, changes, reviews, or diagnoses goroutines, channels,
synchronization, worker pools, or nontrivial context lifetimes. Routine context propagation and
synchronous code do not need it.

Start from the simplest synchronous design. Add concurrency only when independent work, latency,
throughput, or lifecycle requirements justify its extra states and failure paths. Respect the
module's declared Go version before using newer standard-library APIs.

## Define the lifecycle first

Before starting a goroutine, identify:

- who owns it and starts it;
- what successful completion means;
- every exit path, including cancellation and partial failure;
- who waits for it and how its error is observed;
- bounds on concurrent work, queued work, and retained memory;
- who owns and closes each channel.

Prefer structured lifetimes: child work should normally finish before the parent operation returns.
Use the repository's existing task-group pattern. When several sibling operations should cancel on
the first error, `errgroup` is appropriate if the dependency already exists or its value justifies
adding it. Async ownership: request-owned work remains under request
cancellation and completion; work intended to continue needs an existing service/worker that owns,
bounds, observes and shuts it down. Request return must neither abandon work nor accidentally cancel
work meant to continue. This does not require persistence, a workflow framework or extra artifacts;
surviving process restarts is a separate approved requirement.

## Goroutines and shared state

- Keep goroutine creation near the code responsible for waiting or cancellation.
- Pass immutable inputs where practical. When mutable state is shared, make synchronization and
  ownership explicit rather than relying on timing.
- Use a mutex for related state that must change atomically. Use atomics only for small independent
  values whose memory-ordering requirements are clear.
- Do not hold a lock across network, database, channel, callback, or other potentially blocking
  work. Copy the needed state while locked, then release the lock before blocking.
- Bound fan-out according to the actual resource: upstream capacity, database connections, memory,
  file descriptors, or CPU. Do not use a fixed universal goroutine limit.
- When collecting parallel results, preserve any ordering promised by the API; completion order is
  not automatically result order.

## Channels

Use channels for communication or ownership transfer, not merely because work is concurrent. A
mutex is often clearer for protecting shared in-memory state.

- The sending side normally closes a channel because it knows when no more values can arrive.
- Close means "no more values," not "please stop." Use context cancellation or a dedicated signal
  for stopping producers.
- Never close a channel only to release one waiter when a direct result or cancellation path is
  clearer.
- Choose buffering from a concrete backpressure or burst requirement. A buffer can delay blocking;
  it does not remove the need to bound producers and consumers.
- Treat sends and receives as cancellation points when they may block indefinitely.
- A `nil` channel disables its `select` case. Use that deliberately in small state machines, and
  avoid accidental nil-channel waits.
- Ensure every error or cancellation path still lets producers, consumers, and waiters exit.

## Context lifetimes

`context.Context` carries cancellation, deadlines, and request-scoped values across a call tree. It
is not a general dependency container or configuration store.

- Accept context as the first argument for blocking or request-scoped operations and propagate it
  to the actual I/O boundary.
- Do not replace an active request context with `context.Background()` mid-call.
- Always call the cancellation function returned by cancellable context constructors, even when a
  parent deadline is expected to fire.
- Distinguish caller cancellation from a deadline owned by the current operation when that changes
  retry, logging, or error classification.
- Store only small immutable request-scoped values in context. Use explicit parameters for required
  dependencies and business data.
- Detached work needs an explicit longer-lived owner and appropriate bounds and shutdown, reusing
  existing application lifecycle mechanisms. Replacing the context with `context.Background()` alone
  does not establish ownership. On Go 1.21 and
  later, `context.WithoutCancel` can preserve values while detaching cancellation, but only when
  those values remain valid beyond the caller. Do not preserve caller-specific authorization or
  identity accidentally.
- Use cancellation causes only when callers have a real need to distinguish causes and the module's
  Go version supports the chosen API. Ordinary `%w` error chains remain the default for returned
  failures.

## Verification and diagnosis

Test observable lifecycle guarantees instead of scheduler timing.

- Run focused tests normally, then `go test -race` for affected packages.
- Prefer explicit synchronization, hooks at an existing boundary, or a repository-owned fake clock
  over sleeps. A passing sleep-based test does not prove ordering or cleanup.
- Use `testing/synctest` only when the module's Go version supports the required API and the behavior
  depends on goroutine scheduling or time. Keep assertions about outcomes, not implementation
  steps.
- For intermittent failures, repeat the focused test with `-count` after making it deterministic
  enough to diagnose. Repetition can expose a race but does not replace the race detector.
- For a hang, capture all goroutine stacks and inspect blocked send, receive, lock, and wait paths
  before changing code.
- Verify shutdown and error paths, not only successful completion. A result is incomplete if work
  can outlive its owner or block forever after cancellation.

## Review checklist

- Is concurrency required, or would synchronous code be simpler and sufficient?
- Does every goroutine have an owner, bound, exit path, waiter, and observed error?
- Can cancellation reach every blocking operation?
- Can a channel send, receive, lock, or waiter remain blocked after another branch fails?
- Are channel closure and mutable-state ownership unambiguous?
- Are locks released before blocking I/O or callbacks?
- Does the test prove lifecycle behavior without depending on sleeps or scheduler luck?
- Has the race detector covered the affected packages?
