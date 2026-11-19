---
name: galdr
description: Use when the user runs /galdr to start or continue a piece of engineering work, or asks which galdr flow fits a request.
disable-model-invocation: true
---

# galdr

galdr is the entry point for engineering work. Pick one playbook, load it, and do its
steps to the end.

## 1. Start

1. Before you work in a repository, read `git status` and the remotes. Fetch the
   upstream if one exists. Never discard work. Never invent an upstream. Never rewrite
   pushed history. Never force a push.
2. If the runtime has a skill for the main language of the work, load it before you
   design or edit anything.
3. Pick the playbook:

   | Request | Playbook |
   |---|---|
   | A question, a critique, "what do you think", or anything that is not clearly a change | `investigate` |
   | New behavior, or a change to existing behavior | `feature` |
   | Existing behavior that is wrong | `bug` |
   | Structure or performance pain, with no new behavior | `refactor` |
   | A design question that throwaway code answers faster than discussion | `prototype` |

4. Write one line: `galdr: <playbook>, <reason>`. Then read
   `references/playbook-<playbook>.md`, and only that one. If the user names a different
   playbook, use it.

## 2. Skills that the user calls

`shape`, `review` and `handoff` are user-only, so you cannot load them. When a playbook
needs one, stop and give the exact command, for example "Next: run `/galdr:shape`."
`prove` and `debug` load when they apply. Obey them.

## 3. Plan

- A clear routine change that the user asked for needs no plan file. Write the approach
  and a task checklist in your reply, then start.
- Other work has one plan file. Keep it local and do not commit it, unless the
  repository commits its plans. When you write or continue a plan, read
  `references/plan-format.md` and use it. Keep the sections that `shape` wrote.
- Write each item in full. Do not write "TBD", "similar to task N" or "handle edge
  cases".

Code starts after one approval of the whole plan. A clear request for a routine change
is that approval. A material change to scope or risk needs a new approval. Silence, a
tool permission, auto mode or "continue" is not approval of scope.

Before you continue earlier work, and after a context compaction, read the state: the
status line, `git status`, and each recovery folder. Never repeat a write if you do not
know its result. If a review is pending, recover it before you start a new one. Then
continue from `next:`. Keep the status line, the checkboxes and Progress current.

## 4. Do the tasks

**Cheap mode** (default): do the tasks yourself, in order. Each task follows `prove`.

**Thorough mode**: use it for independent tasks that need their own context, or when the
user asks. Give each task to one subagent. Its brief holds the goal, the only files that
it can change, the tests, the acceptance commands and the base commit. It returns one
status (`complete`, `blocked`, `needs-decision`, `failed`) and evidence lines. Do not give
the same file to two parallel subagents. Give mechanical tasks (renames, moves, generated
code) a cheaper model when the runtime lets you choose. A subagent report is a claim. Read
the diff and compare it with the brief. Then examine quality and run the checks yourself.

Continue until you complete all tasks. Stop only for these events:

- a decision that only the user can make
- a plan that contradicts itself or the code
- a task that failed three times
- a necessary independent review with no reviewer available (§5 step 2)
- a browser approval that the user asked for (§5 step 4)
- a user interrupt

A passing check or commit is not a stop. Never end a reply with a plan to act. Do the act.

## 5. Close out each logical unit

A logical unit is one change that you can review and commit alone. After each unit, do
these steps:

1. Read `SKILL.md` in the `review` skill folder next to this one. Decide the depth. For
   prose, configuration or a mechanical edit, a direct check is sufficient. For a
   behavior change, apply its Spec and Quality checks to the unit.
2. Decide on independent review as review §2 tells you. Write the decision and its
   reason in one line in Progress, or in the report when no plan file exists.
3. Fix the gaps in scope. Run the affected checks again. P0 and P1 findings block. P2
   findings are optional.
4. Commit the unit. Commit only the files of the task. Write a short subject and two
   body lines at most. Do not add internal IDs, AI attribution, `Co-Authored-By` lines
   or generated-with footers. If the user asked for browser approval, stop with "Next:
   run `/galdr:review`" before the commit. When the gate approves, commit as the gate
   tells you, then do step 5.
5. Add the evidence to Progress (or to the report), move `next:` forward, and start the
   next unit.

## 6. Engineering rules

- **Cheapest solution first:** no change, then existing code, the standard library, a
  platform or database feature, an installed dependency, and new code last. Read the
  real code path and its callers before you choose. New code does not copy, share or
  call a workaround, a deprecated API or a suppressed rule. Report it.
- **Simplest structure:** obey the Structure item of review §4. Copy code locally only
  when the copies can change independently.
- **Structure before edits:** decide where the change goes, which boundary it crosses,
  which interface it exposes and who owns its state.
- **Scope:** build only the approved work. Change only the code, callers, tests and docs
  that it needs. Report unrelated defects. Do not fix them.
- **Corrections become checks:** when the user says that you made a mistake, or a
  finding can occur again, propose a check that stops it. In order: an API or structure
  change that makes the mistake impossible, a lint rule whose message names the fix, a
  type, a test. A `CLAUDE.md` or `AGENTS.md` line is last. Count the existing
  occurrences. Add the check and change them only after the user approves.
- **Safeguards:** never weaken validation, data-loss protection, security, privacy,
  authentication, authorization, accessibility, a stated requirement or a repository
  check to make a change pass.
- **Questions:** ask only what changes the result and what reading, running or a
  default cannot settle. Ask one question in each message, with your recommendation
  first, and at most 3 before the plan. The other decisions become assumed decisions.
- **Schema or migration:** read `references/migrations.md` before you design it.
- **External actions:** ask before you delete or overwrite data, or write to a shared
  environment. Ask before an action that changes data outside the repository, costs
  money, exposes private data, contacts a person, deploys, publishes, pushes or merges.
  Never ask for a secret in chat.
- **Finish the action:** when the user approves a specific action, do it yourself, in
  the browser if necessary. Do not give the last step back. The approval covers only
  that action. It never covers the next action or an approval of your own review gate.
  Plan approval, "approved" or "continue" is not a go to merge, push, open a PR or
  deploy. Ask for that action by name.
- **Voice:** write in ASD-STE100 Simplified Technical English. Use the strict form for
  briefs, procedures and errors. In the strict form, each sentence has one instruction
  and 20 words at most. Use active voice, simple tenses, no phrasal verbs and no
  semicolons. Replies, plans and reports use the same sentence rules with a free
  vocabulary. Explain each ID and commit SHA. Give a recommendation and its reason. Do
  not use em dashes.

The order of priority is: user instruction, repository instructions, galdr, default
behavior.

## 7. Finish

1. Examine the full result against the plan, not only each task.
2. Run the full check set that `prove` names. State the failed and skipped counts.
3. If the whole result needs one independent review, do it now, unless an earlier
   closeout covered it.
4. Report what changed (one line for each file), the evidence, the risks and **Next**
   (acts or commands).

The default result keeps the branch. Merge, push, open a PR or delete a branch only when
the user gives the go for that action. After a merge, run the full checks again. Make
lockfiles again with their tool, not by hand.
