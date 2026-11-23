# Go Diagnostics and Benchmarking

Read this reference only when the task diagnoses a hang, race, goroutine leak, CPU or memory problem,
latency regression, or makes a performance claim. Routine compiler errors and ordinary focused test
failures do not need it.

Investigate first: reproduce the symptom, trace the real path, form one
hypothesis, and change one variable at a time. The guidance here selects Go-specific evidence and
measurement tools. Respect repository commands, deployment limits, and the module's declared Go
version.

## Match evidence to the symptom

Start with the cheapest evidence that can distinguish the current hypotheses.

| Symptom | First useful evidence |
| --- | --- |
| Intermittent wrong result or crash | Focused reproduction and `go test -race` for affected packages |
| Test or process hangs | Test timeout, all goroutine stacks, then block or mutex profile if needed |
| CPU saturation | CPU profile covering a representative workload |
| Growing live memory | Heap profile by in-use bytes and objects, compared over time |
| Allocation pressure or GC work | Allocation profile, benchmark allocation counts, and runtime metrics |
| Lock contention | Mutex profile; block profile when waiting may include channels or other blocking |
| End-to-end latency | Existing traces first, then goroutine, block, mutex, or CPU evidence for the slow span |
| Scheduler or timing behavior | Execution trace after simpler profiles cannot explain it |

Do not infer a leak from one heap snapshot or a bottleneck from one sample. Compare representative
states and check whether the expensive work is inside the Go process or waiting on a database,
network service, filesystem, or other external resource.

## Diagnostic discipline

- Use `go test -run <pattern>` or the repository's focused equivalent to isolate the symptom.
- Use `-count` to assess repeatability, not to declare a flaky behavior fixed.
- Read race-detector reports from the first conflicting access outward. Fix the ownership or
  synchronization error rather than suppressing the report.
- For hangs, capture complete goroutine stacks before restarting when safe. Identify what each
  blocked goroutine is waiting for and which path was responsible for releasing it.
- Compare heap profiles using the metric that matches the question: live retained memory for leaks,
  allocation volume for churn.
- Use compiler escape diagnostics only after measurements implicate allocations; escape output is
  explanatory evidence, not an optimization target by itself.
- Use `GODEBUG`, execution tracing, or runtime tuning only when simpler evidence is insufficient.
  Restore temporary diagnostic settings after the investigation.
- Protect production profiling endpoints with the deployment's existing access controls and network
  restrictions. Profile collection consumes resources; use a bounded duration appropriate to the
  environment and obtain approval for consequential production actions.

A profile identifies where resources are spent. It does not by itself prove why the work is
unnecessary or which change is safe. Trace callers, ownership, and external waits before proposing a
fix.

## Benchmark design

A benchmark should answer one explicit question at a stable boundary.

- Verify correctness separately before measuring performance.
- Benchmark representative inputs, including the size or shape that drives the suspected cost.
- Keep setup outside the measured region unless setup is part of the operation being compared.
- Use `b.ReportAllocs()` or `-benchmem` when allocation behavior matters.
- Use `b.Loop()` when supported by the module's Go version; otherwise use the conventional `b.N`
  loop. Do not raise the module's Go version only to modernize a benchmark.
- Ensure the measured result is consumed or validated so the compiler cannot remove the relevant
  work, without adding unrelated cost to the timed loop.
- Avoid filesystem, network, database, scheduler, or wall-clock noise unless that real component is
  deliberately the subject. Label such a benchmark accurately rather than presenting it as a
  stable microbenchmark.
- Do not encode universal nanosecond or allocation thresholds. Hardware, toolchains, and runtime
  versions change; compare evidence against an owned baseline or invariant.

## Comparing results

Run competing measurements serially on the same machine, toolchain, build settings, CPU policy, and
representative input. Concurrent benchmark runs contaminate one another.

A typical comparison is:

```sh
go test -run '^$' -bench 'BenchmarkName$' -benchmem -count 10 ./path/to/package > old.txt
go test -run '^$' -bench 'BenchmarkName$' -benchmem -count 10 ./path/to/package > new.txt
benchstat old.txt new.txt
```

Use repository commands when they differ. Install no tool merely because this example names it;
prefer an already approved tool, and ask before adding a durable dependency or CI requirement.

- Use multiple samples and a statistical comparison such as `benchstat`; one before/after number is
  weak evidence.
- Keep the environment quiet and note unavoidable differences.
- Compare the metric named by the requirement: latency, throughput, CPU, live memory, or
  allocations. An allocation reduction is not automatically a user-visible latency improvement.
- Report regressions and inconclusive results as honestly as improvements.
- Retain a benchmark in the repository only when it protects a meaningful performance property or
  supports recurring comparison. One-off investigative benchmarks may remain temporary.

## Verification checklist

- Is the symptom reproducible under a representative workload?
- Does the chosen profile or benchmark measure the claimed problem directly?
- Were external waits ruled in or out before optimizing Go code?
- Was one hypothesis changed at a time?
- Were before and after measurements collected under equivalent conditions?
- Does statistical evidence support the claim, including relevant allocation data?
- Did focused correctness tests, the race detector when relevant, and repository gates still pass?
- Are residual uncertainty and environmental limits stated with the result?
