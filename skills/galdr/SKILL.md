---
name: galdr
description: Use when the user runs /galdr to start or resume a piece of engineering work, or asks which galdr flow fits a request.
disable-model-invocation: true
---

# galdr

Entry point for engineering work: pick one playbook, load it, follow it to its last step.

## 1. Pick the playbook

| Request | Playbook |
|---|---|
| Question, critique, "what do you think", anything not clearly a change | `investigate` |
| New behavior, or a change to existing behavior | `feature` |
| Existing behavior is wrong | `bug` |
| Structure or performance pain, no new behavior | `refactor` |
| A design question that throwaway code answers faster than discussion | `prototype` |

Announce it in one line, `galdr: <playbook>, <reason>`, then read
`references/playbook-<playbook>.md` (only the one picked) and follow it to its last
step. If the user names another playbook, switch without arguing.

## 2. Skills the user must call

`shape`, `review` and `handoff` are user-only, so you cannot load them. When a playbook
reaches one, stop and give the exact command: "Next: run `/galdr:review`." `tdd`,
`verify` and `debug` load on their own; follow them whenever they fire.

## 3. Plan file

Change playbooks keep one plan file per piece of work, written before code. When writing
or resuming one, read `references/plan-format.md` and follow it; keep what `shape`
wrote. No "TBD", "similar to task N" or "handle edge cases": write each one out.

Implementation starts after one approval of the whole plan. A clear request for a small
local change is that approval, and its plan can be three lines. A material change to
scope or risk needs approval again. Keep the status line, checkboxes and Progress
current; a new session resumes from `next:` after checking the claimed state.

## 4. Run the tasks

**Cheap mode** (default): do the tasks yourself, in order, one test-first loop each.

**Thorough mode**, for independent tasks that need their own context, or on request:
one subagent per task, briefed with the goal, the only files it may touch, the tests,
the acceptance commands, the base commit, and the return contract: one status (`complete`, `blocked`, `needs-decision`,
`failed`) plus evidence lines, and commits unless browser approval was asked for. Tasks
that touch the same file never run in
parallel. On return, the report is a claim: read the diff, check it against the brief
first and quality second, and rerun the checks yourself.

Keep going until all tasks are done. Stop only when blocked on a decision only the user
can make, when the plan contradicts itself or the code, when one task has failed three
times, or when the user interrupts. A passing check or a commit is not a stopping point,
and a reply never ends on a plan to act instead of the act.

## 5. Engineering rules

- **Cheapest solution first:** no change, then existing code, standard library, a
  platform or database feature, an installed dependency, and only then new code. Read
  the real code path and its callers before choosing.
- **Simplest structure:** no interface only for mocks or a hypothetical second
  implementation. Local duplication is fine when the copies can change independently,
  never for one shared rule. Add concurrency, caches, queues or generalization only
  for a stated need.
- **Scope:** build only what was approved, and change only the code, callers, tests and
  docs it needs. Report unrelated defects instead of fixing them.
- **Questions:** only what changes what gets built and cannot be settled by reading,
  running or a sensible default. One per message, recommendation first, at most 3 before
  the plan; the rest become assumed decisions. Default to the simplest design.
- **Schema or migration change:** read `references/migrations.md` before writing it.
- **External actions:** ask before anything that changes data outside the repo, costs
  money, exposes private data, contacts a person, deploys, publishes, pushes or merges.
  Never ask for a secret in chat.
- **Finish the action:** once the user approved a specific action, carry it out
  yourself, in the browser if needed, instead of handing the last step back. That
  approval covers that exact action only, never the next one, and never approving your
  own review gate.

Repo-specific commands come from the repo's `CLAUDE.md` or `AGENTS.md`. Precedence: user
instruction, then repo instructions, then galdr, then default behavior.

## 6. Finish

1. Run the repo's full check list fresh; state failed and skipped counts.
2. Stop with "Next: run `/galdr:review`." Resume at step 3 once review approves.
3. Commit each verified logical unit not yet committed: task-owned files only, a short
   subject, at most two body lines. Any change after approval voids it.
4. Report: what changed (one line per file), the evidence, and **Next** as numbered acts
   or commands.

The default outcome keeps the branch and reports. Merge, push, open a PR, or delete a
branch only on an explicit go for that action. After any merge, rerun the full checks;
regenerate lockfiles rather than hand-merge them.
