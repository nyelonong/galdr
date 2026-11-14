# Playbook: refactor

For structure or performance pain with no new behavior. Behavior stays the same: the
existing tests pass before and after.

## Structure

1. Name the pain area. Without a named area that hurts current work, there is nothing
   to refactor.
2. Map it read-only (subagents may help; nobody edits): one line per finding, saying
   what it is, where, and why it hurts. Check the repo's backlog or issues first; a
   tracked finding is not new.
3. Rank each finding: blocking current work, compounding (costs more each time the area
   is touched), or cosmetic. Take only the top one; cosmetic findings never get their
   own change.
4. Confirm with the user that the top finding is worth doing, recommendation first.
5. Agree any new domain name before renaming code.
6. Write the plan file (SKILL.md §3). A move that touches several call sites or repos
   uses expand, migrate, contract: add the new path beside the old, move callers one at
   a time behind their tests, delete the old path once a search shows zero callers.
7. Improvements noticed along the way go into the report, not into this change.
8. List the findings not taken, one line each, so the next pass does not rediscover
   them.

## Performance

Only for a stated requirement or measured evidence of a real problem.

1. Find the actual bottleneck by measuring, not by reading.
2. Record a baseline, change one thing, and repeat the same measurement.
3. Keep the simpler code when the result is inconclusive.

Finish (SKILL.md §6). Done when the tests are unchanged and passing, the target finding
or measurement is resolved, and review has approved.
