# Playbook: feature

Use this playbook for new behavior or a change to existing behavior.

1. If the requirements leave open decisions that change the result, stop with "Next:
   run `/galdr:shape`." `shape` writes the top half of the plan. Continue here from that
   file. Skip this step when the requirements are clear.
2. Read the code path of the change and its callers. Decide where the change goes, which
   boundary it crosses, which interface it exposes and who owns its state.
3. Add Design, Before building, Tasks with their proofs, and Review to the plan. If
   `shape` did not run, write the full plan (SKILL.md §3). Get one approval of the whole
   file.
4. Do the tasks (SKILL.md §4). Each task names its proof before the code.
5. Close out each logical unit (SKILL.md §5).
6. Finish (SKILL.md §7).

The playbook is complete when the full checks pass and you give the report.
