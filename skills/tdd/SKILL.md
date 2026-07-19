---
name: tdd
description: Use before writing or changing any production code — features, bug fixes, refactors — and whenever the router announces the tdd-fast-path. Invoke via route or explicit command.
---

# TDD

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

This is a hard rule, not a preference. If you are about to write or edit production
code and no failing test exists for that change yet, stop and write the test first.

## The loop

1. Write one failing test for the next smallest behavior you need.
2. Run it and read the failure. Three outcomes:
   - **Fails as expected** (the assertion fails for the reason you expect) → continue.
   - **Fails wrong** (compile error, wrong exception type, crash before the assertion)
     → fix the test or its setup; do not touch production code yet.
   - **Passes** (green with no production change) → the test asserts nothing useful;
     rewrite it so it fails first.
3. Emit `EV [<task> RED] <test cmd> → FAIL (<expected failure>)`.
4. Write the minimal production code needed to pass — no more than the test requires.
5. Run the test, and the type checker, to green.
6. Emit `EV [<task> GREEN] <test cmd> → PASS`.
7. Commit the test and implementation as one atomic commit — one logical change,
   conventional prefix (`feat`/`fix`/`refactor`/`test`), never mixed. Refactor commits
   made at the wave gate are separate commits, never folded into this one.
8. Move to the next test.

Refactoring is not a loop step. It happens once, at the wave gate, as a pass across the
whole task's tests — not inside this loop.

## Seams

A seam is a declared boundary where a test may substitute a fake or mock for a real
dependency. Seams come from the plan. If the plan does not declare a seam for what
you're testing, stop and ask — don't invent one.

## If code exists before its test

If production code was written before a test for it exists: delete it. Don't keep it
as reference, don't adapt it — delete means delete. Then restart the loop with a
failing test first.

## Tautological-test tells

| Tell | Why it's empty |
|---|---|
| Asserting the mock | Checks that a mock was called, not that real behavior occurred — passes even if the real logic is deleted |
| Asserting the implementation | Restates the code's internals instead of checking an observable outcome |
| Snapshot without intent | Records that something changed, not whether the change is correct |

## Mock gate

A mock is allowed only at a named seam, with a stated reason (why the real dependency
can't run here — for example, a network call, a non-deterministic clock, cost). No
named seam, no mock: use the real dependency, or the test double the plan provides.

## Cadence

In the loop: run the type checker and the one focused test for the file you're
changing. Do not run the full suite here. Run the full suite at wave gates and before
any completion claim.

## Fast path

When route dispatches straight into this skill (announced as `tdd-fast-path`), the
loop and the Iron Law above still apply in full. Fast path skips routing ceremony, not
test-first discipline.

## Rationalizations

| Thought | Reality |
|---|---|
| "Too simple to test" | Simple things break; the test is fast — write it |
| "I'll verify at the end" | Stale evidence is not evidence; verify now |
| "The fix is obvious, skip root cause" | Symptom fixes recur; find the cause |
| "The test is hard to write" | Hard test = design feedback; check the seam |

## Examples

Go, table-driven with testify:

```go
func TestParseAmount(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    int64
		wantErr bool
	}{
		{"valid rupiah", "Rp10.000", 10000, false},
		{"empty string", "", 0, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseAmount(tt.input)
			if tt.wantErr {
				require.Error(t, err)
				return
			}
			require.NoError(t, err)
			assert.Equal(t, tt.want, got)
		})
	}
}
```

TypeScript, vitest:

```ts
import { describe, it, expect } from "vitest";

describe("parseAmount", () => {
  it("parses a rupiah string", () => {
    expect(parseAmount("Rp10.000")).toBe(10000);
  });
  it("rejects an empty string", () => {
    expect(() => parseAmount("")).toThrow();
  });
});
```

For TypeScript work, load `references/ts-conventions.md` before writing test doubles or
parsing at a boundary.
