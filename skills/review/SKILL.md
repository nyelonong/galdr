---
name: review
description: Use when the user runs /galdr:review to review a branch, diff or plan document, or asks for browser approval.
disable-model-invocation: true
---

# review

Review answers one question: is this change right, and is it good? It gives two
verdicts, **Spec** first and **Quality** second. galdr applies the same checks at each closeout. The
user calls this skill for a separate review or for browser approval.

## 1. Set the scope

- The diff: `base...head` and the uncommitted work, or the paths that the user names.
  Make sure that both ends of the range exist and that the diff is not empty.
- The plan file of the work. If no plan exists, say so. The Quality axis still runs.
- If the runtime has a skill for the language of the code, load it before you judge
  the code.

## 2. Decide on independent review

Name the defect that this change can cause, and its effect. Decide from that failure,
not from keywords. Independent review is necessary when a defect can have a material
effect on one of these:

- runtime behavior or a public contract
- data, migrations or database correctness
- security, privacy, authentication or authorization
- concurrency, async ownership, cancellation or resource lifetime
- external systems: network calls, remote changes, real messages, deploys or cost
- an authority or safety boundary: approvals, stop controls, destructive commands,
  secrets, or permission to push or deploy

If you are not sure, treat that doubt as a reason for independent review. Write the
decision in one line, for example "Independent review: necessary. The migration can
delete rows." or "Independent review: not necessary. Only README text changed."

For an independent review, give each axis to a new instance of the galdr `reviewer`
agent. It has no Edit or Write tool. It still has Bash, and only its instructions
forbid writes through the shell. Without that agent, use a new subagent and tell it to
stay read-only. Put the diff, the plan and the checks of this
skill in its prompt. Do not give it a path to obey. The reviewer reports findings and
does not edit.

If independent review is necessary and no subagent is available, stop. Tell the user
the reason. Continue only when a reviewer is available or the user waives the review.

## 3. Spec axis

Report only three types of finding:

- **Missing**: a requirement that is absent or partial.
- **Creep**: behavior that nobody asked for.
- **Wrong**: a requirement that looks complete but is incorrect.

Quote the plan line for each finding. If the plan line is the error, say so and send it
back to planning. Do not change the code to fit a wrong plan line.

## 4. Quality axis

Run the checks that prove names, and report each failure. Then examine these items:

- **Beyond the diff**: for a material change, read the callers, contracts, stored and
  wire formats, downstream readers, lifecycle timing, feature flags and external
  dependencies. List each fact that you cannot prove as a risk.
- **Tests**: each changed test exercises real behavior. A test that asserts a mock,
  copies the implementation, or keeps a snapshot without a purpose is a finding.
- **Structure**: these are findings. An interface only for mocks or for an imagined
  second implementation. A copy of one shared rule. Concurrency, caches, queues or
  generalization without a stated need.
- **Async ownership**: each goroutine, task, job or listener has an owner and a
  cancellation or shutdown path. Its failures reach the caller or a log.
- **Comments are guilty.** Every comment, docstring and suppression in scope, new or
  old, stays only if it is one of these:
  1. a legal or license header
  2. a compiler, build, code-generation, cgo or generated-file directive
  3. non-obvious behavior forced by an external dependency, platform or protocol
  4. a non-obvious constraint or decision backed by code or contract evidence, which
     includes the reason that an ignored error is safe
  5. public API documentation that defines a contract
  6. an issue or RFC link recording a constraint code cannot express
  7. a style-only suppression of a faulty or pedantic rule

  Narration, banners, tutorials, commented-out code and restatements go. A suppression
  of a correctness or safety rule (`@ts-ignore`, `//nolint`, `eslint-disable` on a real
  rule) is a finding. Mark each comment `KEEP`, `KILL`, `RESHAPE` or `OPEN`. A safety
  constraint that you cannot prove stays `OPEN`, not `KILL`.

A documented standard of the repository has priority over these checks. Do not check
what a linter already enforces.

## 5. Findings and verdicts

Reproduce or refute each finding before you report it. Report the remaining findings
through `ReportFindings` if the host has it. If not, use a table with the columns
`Axis | Priority | File:line | Finding | Plan line or rule`.

- **P0** and **P1** findings block. Fix them before the commit.
- **P2** findings are optional. Do not grow the scope to fix them.

```
## Spec
Verdict: PASS | PASS WITH NOTES | FAIL. Worst: <finding or "none">
## Quality
Verdict: PASS | PASS WITH NOTES | FAIL. Worst: <finding or "none">
```

Never merge the two verdicts.

## 6. Browser approval

When the user asks for browser approval of a diff or a plan document, read
`references/gate.md` and do its steps.

## 7. Receive findings

A finding is a claim. Examine it against the code before you fix it. If two findings
conflict, the user has priority over this review. This review has priority over an
external tool. A change after a verdict or an approval cancels it.

Resolve the findings once. After a fix that changes reviewed behavior, run the focused
checks and one focused follow-up review. A new P0 or P1 finding in that follow-up needs a
new decision or the user. Do not start a third round on your own.
