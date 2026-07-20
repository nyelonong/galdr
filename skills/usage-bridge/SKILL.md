---
name: usage-bridge
description: Use when the user runs /galdr:usage-bridge to install, remove, or check galdr's statusline rate-limits bridge on this machine — the wrapper that makes the usage % and quota-park work. Run install once per machine; uninstall to fully revert; status to check.
---

# usage-bridge

Install, remove, or check the statusline wrapper that feeds galdr its usage numbers.

> Claude-only: this skill wraps the Claude Code `statusLine`, which only Claude
> exposes. On Codex and Antigravity there is no `statusLine` to wrap, so the bridge
> is a documented no-op there — run it only on Claude Code.

## Why a statusLine wrapper

Claude Code hands the official `rate_limits` block only to a `statusLine` command — not
to hooks. So galdr's usage % and quota-park need a `statusLine` wrapper that caches
those numbers each render, then delegates to whatever statusline the user already had.

The wrapper ships in this plugin at `scripts/usage-bridge.sh`. Find it relative to this
skill's base directory (`../../scripts/usage-bridge.sh`) or via `$CLAUDE_PLUGIN_ROOT`.

All installed state lives at stable `~/.claude` paths so it survives plugin version
bumps:

- `~/.claude/galdr/usage-bridge.sh` — the copied wrapper the statusline runs.
- `~/.claude/galdr/original-statusline` — the user's prior statusLine command, saved
  verbatim so the wrapper can delegate to it.

The cache the wrapper writes is `~/.claude/rate-limits-cache.json`.

## Rules (all three modes)

- Never rewrite the user's existing statusline. Wrap it and restore it — the wrapper
  delegates to the saved original.
- Confirm before any write. Show the exact change first.
- Edit `~/.claude/settings.json` atomically: `jq` to a temp file, then `mv` over the
  original. Preserve every other key.
- Fully reversible: uninstall returns settings.json to exactly its pre-install state.

## Mode: install

1. Read `~/.claude/settings.json` and its current `.statusLine.command`.
2. **Idempotent check.** If that command already points at
   `~/.claude/galdr/usage-bridge.sh`, report already-installed and stop. Write nothing.
3. **Show the change, then ask.** Before writing anything, show the user:
   - Files to be created: `~/.claude/galdr/usage-bridge.sh` and (only if a prior
     statusLine exists) `~/.claude/galdr/original-statusline`.
   - The `.statusLine.command` before and after:
     - before: the current value (or "none").
     - after: `bash "$HOME/.claude/galdr/usage-bridge.sh"`
   Ask for explicit confirmation. Do not proceed without it.
4. **On confirm:**
   - `mkdir -p ~/.claude/galdr`.
   - Copy the plugin's `scripts/usage-bridge.sh` to
     `~/.claude/galdr/usage-bridge.sh`, then `chmod +x` it.
   - If a prior `.statusLine.command` exists, save its exact string to
     `~/.claude/galdr/original-statusline` so the wrapper delegates to it. If there was
     no statusLine before, do **not** create that file — the wrapper renders its own
     minimal line instead.
   - Set `.statusLine.command` to `bash "$HOME/.claude/galdr/usage-bridge.sh"` via an
     atomic `jq` edit (temp file then `mv`), preserving every other key.
5. Report done: the new statusLine command and the wrapper path.

## Mode: uninstall

1. Read `~/.claude/settings.json`.
2. Restore `.statusLine.command`:
   - If `~/.claude/galdr/original-statusline` exists and is non-empty, set
     `.statusLine.command` back to its contents.
   - Otherwise remove the `.statusLine` key entirely — the user had no statusline
     before install.
   - Either way, use an atomic `jq` edit (temp file then `mv`) that preserves every
     other key.
3. Delete `~/.claude/galdr/usage-bridge.sh` and
   `~/.claude/galdr/original-statusline`.
4. Report done: settings.json is back to its pre-install state.

## Mode: status

Report, without writing anything:

- **Installed?** Whether `.statusLine.command` in `~/.claude/settings.json` points at
  `~/.claude/galdr/usage-bridge.sh`.
- **Wrapper path:** `~/.claude/galdr/usage-bridge.sh` (note if the file is missing).
- **Cache freshness:** the `cached_at` age from `~/.claude/rate-limits-cache.json` —
  how many seconds old the cached rate limits are (note if the cache file is missing).
