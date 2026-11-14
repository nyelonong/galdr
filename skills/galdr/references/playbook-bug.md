# Playbook: bug

For existing behavior that is wrong.

1. Reproduce it and find the root cause before changing code (the `debug` skill). State
   the cause with its evidence.
2. Write a test that fails because of the bug, and watch it fail for that reason.
3. Make the smallest fix that passes it, then run the full check list.
4. A fix that spans more than one task gets a plan file (SKILL.md §3). A one-task fix
   records the cause and evidence in the report instead.
5. Finish (SKILL.md §6).

Done when the reproducing test passes, the full checks pass, and review has approved.
