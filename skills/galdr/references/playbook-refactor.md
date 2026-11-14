# Playbook: refactor

Use this playbook for structure or performance pain with no new behavior. The behavior
does not change. The existing tests pass before and after.

## Structure

1. Name the area that hurts current work. If no area hurts, do not refactor.
2. Map the area read-only. Write one line for each finding: what it is, where it is,
   and why it hurts. Skip findings that the issues of the repository already track.
3. Rank each finding: it blocks current work, its cost grows each time, or it is
   cosmetic. Take only the top finding, after the user confirms it. A cosmetic finding
   never gets its own change.
4. Agree on each new domain name before you rename code.
5. Write the plan (SKILL.md §3). A move across many call sites uses three steps:
   - Expand: add the new path next to the old path.
   - Migrate: move the callers one at a time, each with its tests.
   - Contract: delete the old path when a search shows zero callers.
6. Report the improvements that you saw and the findings that you did not take, one
   line each. Do not put them in this change.

## Performance

Use this section only for a stated requirement or for measured evidence of a real
problem.

1. Find the actual bottleneck with a measurement. Do not guess from the code.
2. Record a baseline. Change one thing. Do the same measurement again.
3. If the result is not clear, keep the simpler code.

Close out each unit (SKILL.md §5), then finish (SKILL.md §7). The playbook is complete
when the tests pass without changes and you resolve the target finding or measurement.
