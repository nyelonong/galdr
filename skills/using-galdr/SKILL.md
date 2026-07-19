---
name: using-galdr
description: Use when unsure which galdr skill to invoke, or when two skill names seem to overlap (shape vs prototype, review vs verify, debug vs tdd, plan vs waves).
---

# Using galdr

galdr is 15 skills covering the path from an idea to a merged branch, plus a small set
that runs inside every task. This file lists what each skill is for, how they connect,
and which one to pick when two seem to overlap.

## Main flow

shape → plan → waves → review → branches

- **shape** — turns a fuzzy idea into a spec (grill mode: you have a position to test;
  explore mode: no position yet; synthesis mode: requirements are already clear).
- **plan** — turns a spec into a wave-based task list (a DAG of tasks with dependencies).
- **waves** — runs the task list, wave by wave, with an evidence gate at each wave's end.
- **review** — checks a task or a branch against the spec and against code quality.
- **branches** — finishes the branch: runs gate checks and a smoke-test sheet, keeping
  the branch and reporting by default; merge or push only on your explicit instruction.

## On-ramps

route reads the request and picks an entry point above, or one of these direct entries:

- **debug** — a reported bug or unexpected behavior.
- **prototype** — a design question you can answer faster by building a throwaway than
  by writing a spec.
- **rearchitect** — architecture pain with no specific feature attached.

## Always-on core

These apply inside whichever destination above is active, not as separate stops:

- **tdd** — the red-green loop used inside every task in waves.
- **verify** — the evidence check run before any completion claim.
- **continue** — the memory.md / memory-progress.md protocol, plus quota-handoff when a
  session hits its usage limit.

## User-only

Outside routing: **authoring** (write/edit a skill) and **setup** (wire galdr into a repo).

## Telling confusable pairs apart

- **shape vs prototype** — shape interviews you and produces a written spec; prototype
  skips the interview and builds working throwaway code to answer the question directly.
- **review vs verify** — review is a separate reviewer's judgment against the spec and
  code quality; verify is running the actual gate commands yourself and reading the output.
- **debug vs tdd** — debug is for behavior that already exists and is wrong: find the
  root cause first. tdd is for behavior that doesn't exist: write the failing test first.
- **plan vs waves** — plan decides what the tasks are and how they depend on each other;
  waves executes those tasks and gates on evidence.

## Precedence and setup

Precedence: user instruction > project CLAUDE.md > galdr > default behavior.
If this repo has no galdr block in its CLAUDE.md yet, run `/galdr:setup` first.
