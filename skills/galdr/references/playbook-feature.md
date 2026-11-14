# Playbook: feature

For new behavior or a change to existing behavior.

1. If the requirements leave open decisions that change what gets built, stop with
   "Next: run `/galdr:shape`." Resume here with its spec. Clear requirements skip this.
2. Read the code path the change runs through and its callers, then write the plan file
   (SKILL.md §3) and get it approved.
3. Run the tasks (SKILL.md §4), each one test-first.
4. Check each task's evidence before marking it done; record the evidence line in the
   plan file and advance `next:`.
5. Finish (SKILL.md §6).

Done when review has approved the branch and the report is written.
