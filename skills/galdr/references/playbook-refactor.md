# Playbook: refactor

For structure or performance pain with no new behavior. Behavior stays the same: the
existing tests pass before and after.

## Structure

1. Name the pain area that hurts current work; with none, there is nothing to refactor.
2. Map it read-only: one line per finding (what, where, why it hurts), skipping what the
   repo's issues already track.
3. Rank each: blocking current work, compounding, or cosmetic. Take only the top one,
   confirmed with the user; cosmetic findings never get their own change.
4. Agree any new domain name before renaming code.
5. Write the plan (SKILL.md §3). A move across several call sites uses expand, migrate,
   contract: new path beside the old, callers moved one at a time behind their tests,
   old path deleted once a search shows zero callers.
6. Report improvements noticed along the way, and the findings not taken, one line each;
   none go into this change.

## Performance

Only for a stated requirement or measured evidence of a real problem.

1. Find the actual bottleneck by measuring, not by reading.
2. Record a baseline, change one thing, and repeat the same measurement.
3. Keep the simpler code when the result is inconclusive.

Finish (SKILL.md §6). Done when the tests are unchanged and passing, the target finding
or measurement is resolved, and review has approved.
