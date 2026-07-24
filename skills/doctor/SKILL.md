---
name: doctor
description: Use when checking or repairing galdr's wiring on this machine or in this repo — a fresh install, a fresh-repo check, or "is galdr actually working" style questions. Slash-command only, not router- or model-invoked.
disable-model-invocation: true
---

# doctor

Run `scripts/galdr-doctor.sh` and explain what it reports. The script is the single
source of truth for what each check does and its result space; do not restate its
check table here, read the script if you need the exact logic for a check.

## Run it

- Installed from a plugin cache: `bash "$CLAUDE_PLUGIN_ROOT/scripts/galdr-doctor.sh"`
  (no flags needed — it locates its own plugin root and uses the real `$HOME` and
  cwd).
- Dev checkout (working in the galdr repo itself): `bash scripts/galdr-doctor.sh` from
  the repo root, same way.
- The script's `--home` and `--plugin-root` flags exist for the test harness only; a
  normal run never needs them.
- Both forms print one `DOCTOR <check> <OK|FAIL|ADVISE|N/A> <detail>` line per check,
  then a summary line. Exit 1 means at least one check FAILed (wiring is genuinely
  broken); exit 0 covers OK-only and ADVISE/N/A-only runs.

## Explain the result, never fix it

**NEVER run a suggested fix yourself.** The detail text on every non-OK line already
names the exact command; your job is to surface it and let the user decide and run it.
This mirrors usage-bridge's own consent rule: doctor diagnoses, it doesn't act.

- **FAIL** — wiring is broken (the enabled flag is missing, the hook isn't registered,
  or the live emission doesn't match `hooks/bootstrap.md`). Read the detail text and
  hand back its command verbatim: touching the enabled flag, or `chmod +x` on
  `hooks/session-start`, or similar.
- **ADVISE** — not broken, but worth acting on: version drift between the plugin cache
  directory and `plugin.json` (suggest re-syncing the plugin: reinstall or update it),
  usage-bridge not installed (suggest `/galdr:usage-bridge install`), or no per-repo
  config (suggest `/galdr:setup`).
- **N/A** — nothing to report for this machine or host (for example, no statusline
  context because usage-bridge isn't relevant here). Not a problem, don't chase it.

Report every non-OK line in the same order the script printed it, pairing each with
its suggested command. If every line is OK, say so plainly and stop — there's nothing
to recommend.

## Rules

- The script never mutates anything by design (fixes are suggested text, never
  executed commands) — don't add a "just fix it for you" step on top of it.
- Don't reinterpret a check's severity. FAIL is always wiring-broken, ADVISE and N/A
  never warrant an exit-1 framing even if you'd personally prioritize fixing them.
- If the script itself errors (not present, not executable), say so and point at
  `scripts/galdr-doctor.sh` rather than guessing at what it would have found.
