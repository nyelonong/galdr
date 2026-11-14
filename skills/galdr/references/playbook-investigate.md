# Playbook: investigate

Use this playbook for questions, critiques and "what do you think" requests. Do not edit
files. Do not write a plan file. Do not commit.

1. Start from the question as the user asked it. Restate it only when two readings lead
   to different answers.
2. Collect evidence. Read the code, docs, config and logs that the question depends on.
   Run read-only commands. Find facts yourself. Do not ask the user for them.
3. Answer in this order:
   - The verdict, in one line.
   - The support. Cite each claim as `path:line`, as a short command output, or as a
     link. Mark each claim that you did not check as unverified.
   - The critique: what is weak, what is risky, or what is more complex than the need.
     Give the simplest alternative.
   - One recommendation, with its reason.
4. If the recommendation is a change and the user agrees, go to the playbook for that
   change (`feature`, `bug` or `refactor`). Write the decision into its plan.

The playbook is complete when the user has a cited answer that ends with one
recommendation.
