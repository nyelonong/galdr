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
to protect against. Formats:

- Step in progress: `**WIP** <step> — next: <exact command or action>`
- Dispatch in flight: `**WIP** dispatched <brief path> @<base sha> scope=<paths> — next: review on return`
- Decision landed (written by shape the moment it's reached, mid-interview, not tied
  to a step boundary): `DECISION [<topic>] <question> → <choice>`

`<step>` names the unit of work; `next:` is the exact command or action to run on
resume, not a description of intent.

## 2. Task completion

When a step finishes: append `DONE <step> — <summary> @<sha>` to memory-progress.md —
the closure a step WIP needs (§3 detection keys on it) — then refresh only memory.md's
"Current State". Leave Locked Decisions and Domain terms alone unless the task changed one.

## 3. Resume procedure (same agent, later session)

1. Read memory.md in full.
2. Detect crashes before acting on any `next:` line: scan the live memory-progress.md
   in file order. A WIP line is open when no closure for it appears later in the
   file. Closures — dispatch WIP: its `EV [waves] <task-id> return reviewed` line,
   its `LOST-RISK` line, or its `EV [recovery]` line; step WIP: its `DONE` line, its
   `EV [recovery]` line, or a later `CLOSEOUT`/`RELEASED` marker. Detection never
   reads the top-of-file header. Zero open WIP → continue below; any open WIP → the
   last session died unplanned — run §9 first.
3. Find the newest `next:` line in memory-progress.md.
4. Run the command or action it names and read the actual output.
5. Act on what the command showed, not on the prose that preceded it.

This is memory-first: prose claims decay, commands don't.

## 4. Handoff snapshot

What one agent leaves for the next — a later session, a subagent reading a brief, or
a cross-agent handoff to Codex:

- **Verified-claims section**: every claim paired with the exact command that proved
  it this session (for example: "backend tests green — go test ./... run @<sha>").
- **`UNVERIFIED:` prefix** on every claim not command-checked this session — a claim
  carried over from an earlier snapshot or from recollection stays `UNVERIFIED:`;
  sounding certain is not the same as being checked.
- **Suggested-skills list**: which galdr skills the next agent will likely need.
- **Purpose-of-next-session line**: one sentence stating what the next session is for.
- **Dedup by reference**: point at the canonical file (memory.md, a spec, a brief)
  instead of pasting its content into the snapshot.

## 5. Receiver duty

Whoever picks up a handoff snapshot re-verifies every claim before building on it. An
`UNVERIFIED:` label is not a green light with a caveat; it is a to-do. A claim without
a command behind it is not evidence, no matter who wrote it. The duty is identical for
cross-session resume, subagent briefs, and Codex handoffs — no trusted-source exception.

## 6. Hard park

Triggers — this list replaces the old one: a battery or shutdown warning, a hard limit
already hit, or the user says "park now" (or the equivalent — urgency phrasings only).
Soft triggers — a usage limit warning this session, a quota threshold reached, the
user says "park it" — belong to waves' soft park (`skills/waves/SKILL.md`), which
stops before the next dispatch and lets in-flight work finish. Hard park never waits:
not for an in-flight dispatch, not for the current edit. Target: under two minutes,
because the trigger often arrives late.

Park in this order, and do nothing else first:

1. Commit uncommitted work as `wip: park — <state>`. The atomic-commit rule has
   exactly two sanctioned `wip:` forms: `wip: park — <state>` (this step) and
   `wip: crash-salvage — <desc>` (§9 step 4). No other `wip:` use is sanctioned.
2. Close each in-flight dispatch WIP by appending
   `LOST-RISK <task-id> <brief path> @<base sha>` — the return is forfeited; §9
   recovers whatever landed.
3. Write the handoff snapshot (§4), `UNVERIFIED:` on anything not command-checked
   this session.
4. Write the resume header at the top of memory-progress.md — a human pointer only
   (same-agent resume: §3; other-agent: §5). Detection never reads it.
5. Append `PARKED <date> — <soft|hard>: <reason>` — the last ledger act — and commit the ledger.

A clean park closes every WIP line, so the next session's detection finds zero open
WIP. Anything not flushed in steps 1–5 is named in the snapshot, so the next agent
re-derives it instead of assuming it survived.

## 7. Progress-log rotation

At cycle close (`branches` finish, after the closeout/release line; also on explicit
request), move closed-cycle lines out of the live memory-progress.md into an
append-only memory-progress-archive.md (same directory), so the resume read and `EV`
greps stay fast on a long-lived repo.

Boundary: a cycle is closed when its block ends in a `CLOSEOUT` or `RELEASED` marker —
archive up to the last such marker, keep everything after it live. Always keep live:
the newest `next:` line, any still-open WIP, and a one-line header pointing at the
archive (`archive: older closed cycles in memory-progress-archive.md`) — the §3 read
must still find them in the live file.

Move-only, nothing lost: append the moved block to the archive in original order;
never delete or rewrite archived content. `grep '^EV' memory-progress*.md` returns the
full history across both files. The move is a normal committed edit under the standing
atomic-commit rule — no new consent step, no `wip:` exception.

## 8. Memory Current State rotation

Same rule as §7 in narrative shape: memory.md's Current State keeps a few recent
releases inline. Format: one paragraph per release, blank-line separated, starting
with `**<version>** — <date>: ` — the split point rotation needs.

Trigger: same as §7, but only once more than 3 release paragraphs are inline. Keep the
last 3 inline, the trailing NOTE bookkeeping paragraph, and a header pointing at the
archive (`archive: releases older than the last 3 live in memory-archive.md`); move
older paragraphs, oldest first, to memory-archive.md (same directory). Move-only,
append in order, never rewrite the archive; commit is a normal edit — no new consent
step.

## 9. Crash recovery

Entered from §3 detection (open WIP lines = unplanned death), and on resume after a
hard park: classify its `LOST-RISK` dispatches via step 3. Ledger and git only. In order:

1. Inventory the open WIP lines found by the §3 scan.
2. Orient: `git status`, then `git log` from the newest ledger `@<sha>` anchor —
   orientation only, never the classification window.
3. Classify each open dispatch from its OWN recorded base, by the commits in
   `<base sha>..HEAD` touching its scope paths: closure line present → reviewed,
   skip; commits but no closure → returned-unreviewed, run waves' two-verdict review
   now; no commits → lost, re-dispatch from the brief.
4. Dirty tree: diff it, match the diff against the open WIP lines, commit it as
   `wip: crash-salvage — <desc>`, label it UNVERIFIED in the snapshot. Never discard,
   never stash.
5. Append `EV [recovery] <task-id|step> classified=<reviewed|unreviewed|lost|salvaged> @<sha>`
   per handled WIP. These are closures: a finished recovery leaves zero open WIP, so
   the next session detects nothing — recovery must terminate.
6. Append `CRASH <date>: <what died> — recovered: <counts per class>`.
7. Write the §4 handoff snapshot — every claim `UNVERIFIED:` unless command-checked
   during recovery.
8. Exit into §3 and resume normally.
