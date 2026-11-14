# Playbook: investigate

For questions, critiques and "what do you think" requests. Read-only: no edits, no plan
file, no commits.

1. Start from the question as asked. Restate it only when two readings would lead to
   different answers.
2. Gather evidence: read the code, docs, config and logs it depends on, and run
   read-only commands. Settle facts by checking, not by asking the user.
3. Answer in this order:
   - The verdict, one line.
   - The support: every claim cited as `path:line`, trimmed command output, or a link.
     Mark anything you did not check as unverified.
   - The critique: what is weak, risky or more complex than the need, and the simplest
     alternative.
   - One recommendation, with its reason.
4. If the recommendation is a change and the user agrees, switch to the playbook that
   fits it (`feature`, `bug`, `refactor`) and carry the decision into its plan file.

Done when the user has a cited answer that ends in one recommendation.
