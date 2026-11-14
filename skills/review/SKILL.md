---
name: review
description: Use when the user runs /galdr:review to review a branch, diff or plan document, optionally with browser approval.
disable-model-invocation: true
---

# review

Reviews a change on two axes, **Spec** first and **Quality** second, each with its own
verdict. A human can approve the exact change in the browser gate.

## 1. Pin what is reviewed

- The diff: `base...head` plus uncommitted work, or the paths the user names. Confirm it
  resolves and is not empty before anything else.
- The plan file the work was built from. With none, say so; Quality still runs.

## 2. Independent reviewer

When the change touches runtime behavior, data or migrations, security or privacy,
concurrency, external systems or a public contract, or the user asks, give each axis
to a fresh read-only subagent. Paste the diff, the plan and this skill's checks into its
prompt; never point it at a path to obey. It reports findings and never edits. When no
subagent can be dispatched, say the review is author-only.

## 3. Spec axis

Report only: requirements **missing** or partial, behavior nobody asked for
(**creep**), and requirements that look done but are **wrong**. Each finding quotes the
plan line. When the plan line itself is the error, say so and send it back to planning
instead of patching code to fit it.

## 4. Quality axis

Run the repo's checks and report failures. Then check:

- **Tests:** each changed test exercises real behavior; asserting a mock, the
  implementation's internals, or a snapshot with no stated intent is a finding.
- **Simplest structure:** an interface only for mocks or a hypothetical second
  implementation, duplication of one shared rule, or concurrency, caches, queues or
  generalization with no stated need.
- **Async ownership:** every goroutine, task, job or listener has an owner and a
  cancellation or shutdown path, and its failures reach the caller or a log.
- **Comments are guilty.** Every comment, docstring and suppression in scope, new or
  existing, stays only if it is one of:
  1. a legal or license header;
  2. a compiler, build, code-generation, cgo or generated-file directive;
  3. non-obvious behavior forced by an external dependency, platform or protocol;
  4. a non-obvious constraint or decision backed by code or contract evidence,
     including why an ignored error is safe;
  5. public API documentation that defines a contract;
  6. an issue or RFC link recording a constraint code cannot express;
  7. a style-only suppression of a faulty or pedantic rule.

  Narration, banners, tutorials, commented-out code and restatements go. A
  correctness or safety suppression (`@ts-ignore`, `//nolint`, `eslint-disable` on a
  real rule) is a finding. Mark each `KEEP`, `KILL`, `RESHAPE` or `OPEN`; a claimed
  safety constraint you cannot prove stays `OPEN`, never `KILL`.

A repo's documented standard overrides any check here; skip what a linter enforces.

## 5. Findings and verdicts

Reproduce or refute each finding before reporting it. Report survivors through
`ReportFindings` when the host has it, otherwise as `Axis | Severity | File:line |
Finding | Plan line or rule`. Severity: **Critical** fix before merge, **Important**
fix before the next task, **Minor** note.

```
## Spec
Verdict: PASS | PASS WITH NOTES | FAIL — worst: <finding or "none">
## Quality
Verdict: PASS | PASS WITH NOTES | FAIL — worst: <finding or "none">
```

Never merge the two verdicts into one.

## 6. Browser approval

When the user asks for browser approval of a diff or a plan document, read
`references/gate.md` and follow it.

## 7. Receiving findings

Check each finding against the code before fixing it; a finding is a claim. On
conflict, the user outranks this review, which outranks an external tool. Any change
after a verdict or an approval voids it: fix, rerun the focused checks, review again.
