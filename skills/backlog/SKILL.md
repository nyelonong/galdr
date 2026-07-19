---
name: backlog
description: Use when the user runs /galdr:backlog, or when a skill explicitly defers something to a later cycle — reviews, records, or resolves deferred work in docs/backlog.md, the pack's backlog file.
---

# backlog

Owns `docs/backlog.md` end to end: the entry format, the Open/Resolved structure, the
default list action, the append-on-defer rule other skills follow, and resolve. This
file is the single source of truth for all of that — no other skill restates the
format; they reference this one instead.

## The file

`docs/backlog.md` is the backlog — a fixed convention, like `memory-progress.md`:
always this path, never a per-repo setting (a configurable path is itself a deferred
backlog item, not solved here). It holds deferred work — parked ideas, findings not
fixed yet, and follow-ups — not a task list and not runtime state.

## Entry format

One bullet per item, carrying four fields: what, why, target, source.

```
- **<what>** (target <version/date>) — <why it was deferred, one or two sentences>.
  Source: <where this came from — a spec section, a review finding, a conversation>.
```

Example:

```
- **Rate-limit bridge-installer** (target 0.4) — opt-in setup step so machines
  without the statusline still get real usage %. Source: 0.3 shape.
```

All four fields are required. A bullet missing `target` or `source` is incomplete —
fill it in before appending rather than leaving it for later.

## Structure: Open and Resolved

Two sections, always present, never fewer:

- **Open** — undone work, in the entry format above. This repo's Open section is
  headed `## Features / ideas` (an existing heading recognized as Open); a fresh
  backlog file uses the heading `## Open`.
- **Resolved** — done items, one line each (see Resolve below). This repo's Resolved
  section is headed `## Resolved findings`; a fresh file uses `## Resolved`.

A backlog may also carry other, older sections (for example a pre-convention
"trial-era" dump). Leave those as found — they predate this structure and this skill
does not rewrite them.

Never delete an item outright. A done item moves to Resolved with a note; nothing
that was once tracked silently disappears.

## Default action: list

`/galdr:backlog` with no argument lists the **Open** items only — name, target, and
the one-line why, in file order. Never include Resolved items in this listing: a user
asking what's in the backlog wants what's still outstanding, not the history.

## Append-on-defer

This is the rule `shape`, `plan`, `waves`, `branches`, and `review` each reference
instead of restating. When one of those skills explicitly defers something to a later
cycle — not every passing idea, only a real "this waits" decision — it appends one
bullet to the Open section, in the exact entry format above. Nothing else changes: no
new section, no edit to neighboring bullets.

A user can also ask directly to add an item; the same format and the same rule apply.

## Resolve

When an open item's work lands, move it: remove its bullet from Open, and add one
line under Resolved:

```
- **<what>** — RESOLVED <version/date>: <what changed, one line>.
```

Keep the bold `<what>` name so the item stays findable by name across both sections.
Resolve is explicit — nothing here auto-resolves an item; a skill or the user states
the work is done before the move happens.
