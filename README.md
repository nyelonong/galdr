<p align="center">
  <img src="assets/banner.png" alt="galdr: test-first engineering for coding agents. Shape, plan, build, verify, review, handoff." width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-plugin-6e56cf?style=flat-square" alt="Claude Code plugin">
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-1.0.1-22d3ee?style=flat-square" alt="version 1.0.1"></a>
  <a href="skills/"><img src="https://img.shields.io/badge/skills-7-34d399?style=flat-square" alt="7 skills"></a>
  <img src="https://img.shields.io/badge/discipline-TDD_first-f59e0b?style=flat-square" alt="TDD first">
</p>

<h1 align="center">galdr</h1>

<p align="center">
  <b>Seven small skills that make an AI coding agent work like a careful engineer:<br>
  a failing test before code, fresh evidence before "done",<br>
  and, when you ask, your approval of the real diff before it is committed.</b>
</p>

<p align="center">
  <a href="#the-flow">Flow</a> ·
  <a href="#the-review-gate">Review gate</a> ·
  <a href="#the-skills">Skills</a> ·
  <a href="#install">Install</a> ·
  <a href="#use">Use</a> ·
  <a href="#how-it-was-tested">Tested</a>
</p>

<p align="center">
  <i>galdr</i>: Old Norse for "incantation." A plugin for Claude Code; the skills also
  install into other agents as plain <code>SKILL.md</code> files.
</p>

---

## Who is this for

You use an AI agent to write code, and one of these is true:

- it writes code without tests, and bugs it "fixed" come back;
- it says "done" and you cannot tell whether it ran anything;
- it builds more than you asked for, or asks you ten questions before doing anything;
- you want to approve the actual change, not the agent's summary of it.

galdr costs nothing until you call it. There is no always-on hook: three discipline
skills load when they apply, and everything else waits for a slash command.

## The flow

```mermaid
flowchart LR
    A([request]) --> G{{/galdr}} --> S[shape] --> P[plan file] --> B[build test-first] --> V[verify] --> R[review + gate] --> Z([committed, your call to push])
    classDef flow fill:#0b1120,stroke:#22d3ee,stroke-width:1px,color:#e0f2fe;
    class A,G,S,P,B,V,R,Z flow;
```

`/galdr` reads the request and picks one playbook:

| Request | Playbook | Ends with |
|---|---|---|
| A question or a critique | `investigate` | A cited answer and one recommendation; nothing edited |
| New or changed behavior | `feature` | Plan file, test-first tasks, review |
| Behavior that is wrong | `bug` | Root cause, a reproducing test, the fix, review |
| Structure or performance pain | `refactor` | One ranked finding fixed, tests unchanged, review |
| A design question code can answer | `prototype` | A recorded decision and a test list; the prototype deleted |

Each piece of work keeps one plan file in `docs/plans/`: the goal and decisions, the
tasks, the evidence lines, and a `next:` line. There is no separate spec, so a new session picks up where the last one stopped.

## The review gate

[`/galdr:review`](skills/review/SKILL.md) checks a change against its plan first and
code quality second, with two separate verdicts. When you ask for it, it opens a local
page that shows you the real working-tree diff, not a description of it, and waits for
your decision:

- **approve** records an approval bound to that exact state;
- **request changes** sends your line comments back to the agent;
- any edit after approval voids it, so `verify` fails at commit time until you look again.

It runs on Python 3.9 or newer with no installs; fonts and scripts are bundled, and the
page loads nothing from the network.

## The skills

| Skill | Loads | What it does |
|---|---|---|
| [`galdr`](skills/galdr/SKILL.md) | `/galdr` | Picks the playbook, keeps the plan file, runs the tasks, finishes |
| [`shape`](skills/shape/SKILL.md) | `/galdr:shape` | Turns an idea into the plan's goal and decisions; checks facts itself and asks at most 3 questions |
| [`tdd`](skills/tdd/SKILL.md) | on its own | No production code without a failing test first |
| [`verify`](skills/verify/SKILL.md) | on its own | No "done" without fresh evidence, skip count included; audits docs against code |
| [`debug`](skills/debug/SKILL.md) | on its own | No fix without a root cause; mitigate first in a live incident |
| [`review`](skills/review/SKILL.md) | `/galdr:review` | Spec and quality verdicts, comments-are-guilty, the browser gate |
| [`handoff`](skills/handoff/SKILL.md) | `/galdr:handoff` | A brief a fresh session can act on, and the report it writes back |

## Example: a rough idea

> "Track when a user opens the pricing page."

`/galdr:shape` reads the code first, so it does not ask which database you use. It
proposes the simplest design that meets the need, a direct write, and lists an event
queue only as a rejected alternative. You get one question at a time, each with a
recommendation, and the top half of one plan file, whose acceptance checks a command
can decide. `/galdr` adds the tasks to that same file, and you approve it once.

## Install

### Claude Code

```
/plugin marketplace add nyelonong/galdr
/plugin install galdr@nyelonong
```

### Other agents

```
npx skills add nyelonong/galdr
```

The skills are plain `SKILL.md` files. The review gate travels inside
`skills/review/`, so it works wherever the skill lands.

### Upgrading from 0.x

1.0 is a breaking release: 22 skills became 7 and the always-on hook is gone. The
[CHANGELOG](CHANGELOG.md) maps every old command to its replacement. Your existing
`memory.md` and `memory-progress.md` files are left alone and no longer read.

## Use

- Start work with `/galdr <request>`.
- Repo-specific commands come from your repo's `CLAUDE.md` or `AGENTS.md`; galdr has no
  config file of its own.
- galdr never pushes, merges, deploys or publishes without your go for that action, and
  once you give it, it finishes that action instead of handing it back.

## How it was tested

Every 1.0 skill was tested before release, with and without its text loaded:

- **Discipline skills under pressure.** `tdd` 4/4, `debug` 2/2 and `verify` 2/2
  scenarios pass with the skill loaded, zero forbidden behaviors. The earlier runs
  without the skill had edited code on a "tests after" nudge, wrapped tests around
  untested code, and mocked on request.
- **Retrieval checks.** `galdr` routed 5/5 requests to the right playbook, `shape`
  5/5 and `review` 4/4 probes pass, and a `handoff` brief let a fresh agent finish a
  task with no other context.
- **The gate.** 230 Python and 28 JavaScript tests, run on Python 3.9 and 3.13.

## Acknowledgments

galdr builds on ideas from [obra/superpowers](https://github.com/obra/superpowers) (MIT)
and [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). It is an
independent implementation.
