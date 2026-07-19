---
name: continue
description: Continuation protocol for resuming work after a break, handing off to another session, a subagent, or Codex, and parking fast under a usage limit. Invoke via route or explicit command.
---

# continue

Keeps work resumable across session death, subagent dispatch, and cross-agent handoff.
Durable state lives only in memory.md and memory-progress.md; this skill is how that
state gets written and read.

## 1. WIP lines: write before, not after

Before starting any multi-step task, append a WIP line to memory-progress.md. Sessions
die mid-step; a WIP line written after the fact does not survive the death it was meant
to protect against — write it before, not after. Not every line this protocol writes is
a WIP line — a decision line below lands the moment it's reached, mid-interview, not
tied to a step boundary.

Formats:
- Step in progress: `**WIP** <step> — next: <exact command or action>`
- Dispatch in flight: `**WIP** dispatched <brief path> @<base sha> scope=<paths> — next: review on return`
- Decision landed (written by shape mid-interview): `DECISION [<topic>] <question> → <choice>`

`<step>` names the unit of work; `next:` is the exact command or action to run on
resume, not a description of intent.

## 2. Task completion

When a task finishes: append a one-line summary to memory-progress.md, then refresh
only the "Current State" section of memory.md. Leave Locked Decisions and Domain terms
alone unless the task explicitly changed one of them.

## 3. Resume procedure (same agent, later session)

1. Read memory.md in full.
2. Find the newest `next:` line in memory-progress.md.
3. Run the command or action it names and read the actual output.
4. Act on what the command showed, not on the prose that preceded it.

This is memory-first: prose claims decay, commands don't.

## 4. Handoff snapshot

A handoff snapshot is what one agent leaves for the next — another session, a
dispatched subagent reading a brief, or a cross-agent handoff to Codex. It has:

- **Verified-claims section**: every claim paired with the exact command that proved
  it this session (for example: "backend tests green — go test ./... run @<sha>").
- **`UNVERIFIED:` prefix** on every claim not command-checked this session, including
  claims carried over from a previous snapshot or from conversation recollection.
- **Suggested-skills list**: which galdr skills the next agent will likely need.
- **Purpose-of-next-session line**: one sentence stating what the next session is for.
- **Dedup by reference**: point at the canonical file (memory.md, a spec, a brief)
  instead of pasting its content into the snapshot.

A claim carried forward from an earlier session without a command run this session
stays `UNVERIFIED:` even if the earlier session sounded certain — sounding certain is
not the same as being checked.

## 5. Receiver duty

Whoever picks up a handoff snapshot — the same agent next session, a subagent reading a
brief, or Codex reading a cross-agent handoff — re-verifies every claim before building
on it. An `UNVERIFIED:` label is not a green light with a caveat; it is a to-do. A claim
without a command behind it is not evidence, no matter who wrote it or how the wording
reads.

This duty applies identically in all three cases: cross-session resume, subagent
briefs, and cross-agent (Codex) handoffs. There is no trusted-source exception.

## 6. Limit-park mode

Trigger: a usage quota is exhausted, a limit warning appears, the user says "park it"
(or the equivalent), or waves' pre-dispatch budget guard parks before a dispatch
(`skills/waves/SKILL.md` § Pre-dispatch budget guard). Target: under two minutes of
agent work, because the trigger often arrives late.

Park in this order, and do nothing else first — no finishing the current edit, no
starting a new one:

1. Commit uncommitted work as `wip: park — <state>`. This repo's atomic-commit rule
   (one logical change per commit) has exactly one sanctioned exception: a `wip:`
   commit for parking unfinished state. Parking mid-task is the declared exception,
   not a habit.
2. Flush WIP lines, including any in-flight dispatches: brief path, base SHA, and
   "returns unreviewed" for each subagent still out.
3. Write the handoff snapshot (§4), with `UNVERIFIED:` labels on anything not
   command-checked this session.
4. Write a resume header at the top of memory-progress.md naming both paths:
   - `resume-same-agent:` — memory-first, verify the claimed state with commands (§3).
   - `resume-other-agent:` — handoff rules apply; the receiver re-verifies before
     building on any claim (§5).

Park skips nothing silently. Anything that did not get flushed in steps 1-4 is listed
as `LOST-RISK: <what and why>` in the snapshot, so the next agent knows exactly what to
re-derive instead of assuming it survived.

## 7. Progress-log rotation

At cycle close, move closed-cycle lines out of the live memory-progress.md into an
append-only memory-progress-archive.md (same directory), so the resume read and `EV`
greps stay fast on a long-lived repo.

Trigger: `branches` finish, after the closeout/release line is written; also on
explicit request.

Boundary: a cycle is closed when its block ends in a `CLOSEOUT` or `RELEASED` marker —
archive the lines up to the last such marker in the file, keep everything after it live.

Always keep live: the newest `next:` line, any still-open WIP (in-flight, not yet
closed), and a one-line header at the top of memory-progress.md pointing at the archive
(example: `archive: older closed cycles in memory-progress-archive.md`). Never archive
the newest `next:` line or open WIP — the memory-first resume read (§3) must still find
them in the live file.

Move-only, nothing lost: append the moved block to the archive in original order; never
delete or rewrite already-archived content. Concatenating the rotated-out region with
the archive reproduces the pre-rotation file exactly; `grep '^EV' memory-progress*.md`
returns the full history across both files.

Commit: the move is a normal committed edit under the standing atomic-commit rule — no
new consent step, no `wip:` exception.
