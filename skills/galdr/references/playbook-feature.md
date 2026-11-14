# Playbook: feature

For new behavior or a change to existing behavior.

1. If the requirements leave open decisions that change what gets built, stop with
   "Next: run `/galdr:shape`." It writes the plan file's top half; resume here from that
   file. Clear requirements skip this.
2. Read the code path the change runs through and its callers, then add Design, Before
   building, Tasks with their proofs, and Review (or write the whole plan, SKILL.md §3),
   and get the whole file approved once.
3. Run the tasks (SKILL.md §4), each against its proof.
4. Check each task's evidence before marking it done; add its line to Progress and
   advance `next:`.
5. Finish (SKILL.md §6).

Done when review has approved the branch and the report is written.
