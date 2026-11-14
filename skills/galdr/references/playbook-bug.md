# Playbook: bug

Use this playbook for existing behavior that is wrong.

1. Reproduce the bug and find the root cause before you change code (the `debug`
   skill). State the cause and its evidence.
2. Write a test that fails because of the bug. Watch it fail for that reason.
3. Make the smallest fix that makes the test pass. Run the full checks.
4. Close out the fix (SKILL.md §5). A fix with more than one task gets a plan file
   (SKILL.md §3). A fix with one task records the cause and the evidence in the report.
5. Finish (SKILL.md §7).

The playbook is complete when the test passes, the full checks pass and the report is
written.
