---
name: setup
description: Use once per repo to create or refresh docs/agents/galdr.md — the config verify, waves, review, branches, and route read for gate commands, invariants, models, and smoke details. Slash-command only, not router- or model-invoked.
disable-model-invocation: true
---

# setup

Per-repo wiring, run once when galdr starts working in a repo and again whenever the
repo's commands, invariants, or models change. Idempotent: re-running never silently
destroys a hand-edited config.

## Procedure: explore → recommend → confirm → write

1. **Explore.** Read the repo for the markers below, any existing
   `docs/agents/galdr.md`, and the repo's own CLAUDE.md. Note what's already there
   before proposing anything.
2. **Recommend.** Build a full draft of `docs/agents/galdr.md` from the detected
   markers and the defaults below. Show the draft in full.
3. **Confirm.** Ask before writing. If `docs/agents/galdr.md` already exists, diff the
   draft against it section by section — see "Human edits" below for the extra rule
   that applies to Gates and Invariants specifically.
4. **Write.** Write the confirmed config, then update the CLAUDE.md galdr block
   (below). Nothing is written before step 3's confirmation.

## Detection heuristics

- **Host agent** → detect Claude vs Codex vs Antigravity up front. The `## Budget`
  usage keys (`rate-limits-cache`, `five-hour-park-pct`, `seven-day-park-pct`,
  `rate-limits-max-age`) are **Claude-only**: on Codex and Antigravity, skip them when
  writing `docs/agents/galdr.md` (see Budget below).
- **Go markers** (`go.mod`) → Gates defaults: `gofmt -l .`, `go vet ./...`,
  `go test ./...`. Note any docker-compose or `make up`-style dependency as a
  docker/skip note next to the test command — tests that skip without it are not a
  clean pass (see verify's skip-count rule).
- **pnpm markers** (`pnpm-lock.yaml`, or a `packageManager` field in `package.json`) →
  Gates defaults: `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm test`.
- **Both present** → both sets of defaults, in the same Gates section.
- **No markers matched** → leave the relevant Gates line as a placeholder and say so at
  the confirm step; do not invent a command for a stack that wasn't detected.

## Config file: docs/agents/galdr.md

Exactly these sections, in this order, every time — no more, no fewer:

- **`## Gates`** — task-level and gate-level command lists, from the detection above.
- **`## Invariants`** — exit-coded scripts run at wave gates and branch finish. Empty
  is allowed; write the heading with nothing under it rather than omitting it.
- **`## Fast path`** — overrides to route's fast-path criteria, if this repo needs any.
- **`## Review sources`** — Standards-axis docs (a design doc, a style guide, a
  mirror-pair rule) the review skill should read.
- **`## Models`** — tier → model id. Defaults: `mechanical: claude-haiku-4-5`,
  `standard: claude-sonnet-5`, `top: session model`. Keep these unless the repo names a
  different binding.
- **`## Worktree notes`** — package manager, env files to copy, and service
  dependencies (docker compose, external services) each worktree needs.
- **`## Smoke`** — launch command, base URL, test account / seed-data notes, and the
  smoke-sheet output dir. Detected defaults: pnpm repo → `pnpm dev` and
  `http://localhost:3000`; Go repo → the repo's make/run target and its API base URL.
- **`## Briefs`** — whether waves' dispatch briefs under `docs/briefs/` are gitignored
  (the default) or committed. State the default explicitly rather than leaving it
  implied.
- **`## Budget`** — four keys, all written idempotently: re-running setup updates each
  key already present in place, never duplicates it, and never re-adds a key the user
  has deliberately removed from the file — a missing key stays missing unless the user
  explicitly asks to add it back. Same respect-rule as Gates/Invariants below, just
  without the extra diff-and-confirm step (there's nothing to overwrite when a key is
  simply absent). **Claude-only:** the rate-limits statusline that
  feeds these keys is a Claude Code feature. On Codex and Antigravity, skip the whole
  `## Budget` section — do not write any of its keys.
  - `rate-limits-cache`, default `~/.claude/rate-limits-cache.json` — the file
    (written by the statusline) galdr reads for 5h/7d usage %.
  - `five-hour-park-pct`, default `90` — waves parks before a dispatch when the 5-hour
    used % is at or above this.
  - `seven-day-park-pct`, default `95` — same idea as `five-hour-park-pct`, for the 7-day
    window (defaulted higher because the 7-day budget recovers more slowly).
  - `rate-limits-max-age`, default `300` (seconds) — a cache older than this is treated
    as unavailable.

  At setup time, surface the two park thresholds for the user to accept or change (they
  are the knob that controls when a run parks); write the defaults (`90` for 5h, `95` for
  7d) only if the user accepts them. All four keys stay editable in the config file
  afterward. Skip this entire step on Codex and Antigravity.

## CLAUDE.md block

Append or replace one block between `<!-- galdr:start -->` and `<!-- galdr:end -->` in
the repo's CLAUDE.md, pointing at `docs/agents/galdr.md` rather than duplicating its
contents. On re-run, replace everything between the two markers; never append a second
block. If the markers aren't present yet, add the block at the end of the file.

## Human edits

Gates and Invariants are the two sections a person is most likely to have hand-tuned
after the last run (an added command, a loosened invariant). Before overwriting either
section on a re-run, show the diff between what's on disk and what this run would
write, and get explicit confirmation — a silent overwrite here is data loss, not a
refresh. The other sections can refresh without this extra step; step 3's confirmation
still covers the file as a whole either way.

## Step 5: roles-and-journeys.md

If `docs/agents/roles-and-journeys.md` does not yet exist, offer the interview that
produces it: read the target repo's own docs/specs/code first, draft what's found,
interview the user only for gaps, and write a cited-only canonical roles doc. If the
file already exists, skip this step on an ordinary re-run — only an explicit refresh
request reopens the interview. Full procedure, output contract, and edge cases:
`references/roles-and-journeys.md`.
