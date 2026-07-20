---
name: core
description: Use when the user runs /galdr:core to install, uninstall, or check galdr's core rules block on this machine for Claude, Codex, or Antigravity. Run install once per agent to write the marked block into that agent's rules file (or the Claude enabled flag); uninstall to remove it; status to report state without writing.
---

# core

Install, remove, or check the galdr core rules block on this machine, per agent.

The core block is the shared §0–§6 bootstrap (memory-first, Iron Laws, routing,
voice, precedence). It ships in this plugin at `carriers/<agent>.md` wrapped
between `<!-- galdr:start -->` and `<!-- galdr:end -->` markers. The installer
writes that marked block into the agent's rules file; uninstall removes the
marked block and preserves everything else.

## Agents and targets

- **Codex** → `~/.codex/AGENTS.md` (block from `carriers/codex.md`).
- **Antigravity** → `~/.gemini/AGENTS.md` (block from `carriers/antigravity.md`).
- **Claude** → `~/.claude/galdr/enabled` flag file (no block — `touch` on
  install, `rm` on uninstall). The session-start hook reads this flag.

All target paths are overridable by env vars (`GALDR_CODEX_TARGET`,
`GALDR_ANTIGRAVITY_TARGET`, `GALDR_CLAUDE_FLAG`, `GALDR_CARRIERS_DIR`) so the
test suite can sandbox them and the real global files are never touched.

## The installer script

`scripts/core-install.sh` is the write mechanism. Run it as:
`bash scripts/core-install.sh {install|uninstall|status} [agent]`
(`agent` defaults to `codex` when omitted; every interaction should name it
explicitly.)

It writes atomically (temp file then `mv`). For Codex / Antigravity:
- target absent → create the file with the marked block;
- markers present → replace the marked region with the block (idempotent —
  never duplicates, even on repeated install);
- target exists without markers → append the marked block, preserving all
  prior content.

`uninstall` removes the marked block (markers included) and preserves
everything else. `status` reports per-agent state without writing.

## Consent layer (this skill's job — modeled on usage-bridge)

The script writes; **this skill owns consent**. Before any write, show the user
the exact change and ask for explicit confirmation. Do not proceed without it.

For `install` / `uninstall` on Codex or Antigravity:
1. Show the **target file** path.
2. Show the **exact block** to write (or the exact block being removed).
3. Show a **before/after diff** of the target file:
   - install over prior content → diff shows prior content preserved, block
     appended;
   - install over markers → diff shows the marked block replaced (not
     duplicated);
   - uninstall → diff shows the marked block gone, prior content preserved.
4. Ask for explicit confirmation. On confirm, run the script.

For `install` / `uninstall` on Claude:
1. Show the **flag file** path (`~/.claude/galdr/enabled`).
2. Show the action: `touch` (install) or `rm -f` (uninstall).
3. Ask for explicit confirmation. On confirm, run the script.

`status` writes nothing — no consent needed. Run the script and report its
output verbatim.

## Rules

- Never write before the user confirms. The script is fast; consent is the gate.
- Never edit the carrier files. They are the source of truth; the script
  extracts the marked block from them as-is.
- Never duplicate the block. If markers are present, replace; only append when
  markers are absent.
- Preserve all non-galdr content. Uninstall removes only the marked block.