#!/usr/bin/env bash
# galdr core installer: install / uninstall / status the galdr core rules block
# for the three agents (claude, codex, antigravity).
#
# Codex and Antigravity: extract the marked block between
#   <!-- galdr:start --> and <!-- galdr:end --> from carriers/<agent>.md and write
#   it into the agent's rules file atomically (temp file then mv).
# Claude: touch / rm the enabled flag the session-start hook reads.
#
# All target paths are overridable by env vars so tests can sandbox them and the
# real global files (~/.codex/AGENTS.md, ~/.gemini/AGENTS.md,
# ~/.claude/galdr/enabled) are never touched.
set -u

START_MARK="<!-- galdr:start -->"
END_MARK="<!-- galdr:end -->"

# Carrier directory: repo-local by default, overridable for sandboxing.
carriers_dir="${GALDR_CARRIERS_DIR:-$(cd "$(dirname "$0")/.." && pwd)/carriers}"

# Target paths (overridable for sandboxing).
codex_target="${GALDR_CODEX_TARGET:-$HOME/.codex/AGENTS.md}"
antigravity_target="${GALDR_ANTIGRAVITY_TARGET:-$HOME/.gemini/AGENTS.md}"
claude_flag="${GALDR_CLAUDE_FLAG:-$HOME/.claude/galdr/enabled}"

usage() {
  cat <<EOF
Usage: $0 {install|uninstall|status} [agent]
  agent: claude | codex | antigravity  (default: codex)
EOF
}

# Extract the marked block (markers included) from a carrier file to stdout.
extract_block() {
  awk -v s="$START_MARK" -v e="$END_MARK" '
    $0 == s { inblock=1 }
    inblock { print }
    $0 == e { inblock=0 }
  ' "$1"
}

# True (exit 0) if the target file exists and contains the start marker.
has_markers() {
  [ -f "$1" ] && grep -qF "$START_MARK" "$1" 2>/dev/null
}

# install_marked <target> <carrier>
# Create with the block if absent; replace the marked region if markers present
# (idempotent — never duplicates); append the marked block if the file exists
# without markers (preserve all prior content). Atomic: temp file then mv.
install_marked() {
  target="$1"
  carrier="$2"
  block=$(extract_block "$carrier")
  tmp="${target}.tmp.$$"
  if [ ! -f "$target" ]; then
    printf '%s' "$block" > "$tmp"
    mv "$tmp" "$target"
    return 0
  fi
  if has_markers "$target"; then
    # Replace the marked region with the new block. Split into before/after so
    # multi-line strings are never passed to awk -v (which warns on newlines).
    before="${tmp}.before"
    after="${tmp}.after"
    awk -v s="$START_MARK" '$0 == s { exit } { print }' "$target" > "$before"
    awk -v e="$END_MARK" '$0 == e { found=1; next } found { print }' "$target" > "$after"
    {
      cat "$before"
      printf '%s' "$block"
      cat "$after"
    } > "$tmp"
    rm -f "$before" "$after"
    mv "$tmp" "$target"
    return 0
  fi
  # File exists, no markers: append the block, preserving prior content.
  {
    cat "$target"
    printf '\n%s' "$block"
  } > "$tmp"
  mv "$tmp" "$target"
}

# uninstall_marked <target>
# Remove the marked block (markers included), preserve everything else. No-op
# if the file is absent or has no markers. Atomic: temp file then mv.
uninstall_marked() {
  target="$1"
  [ ! -f "$target" ] && return 0
  has_markers "$target" || return 0
  tmp="${target}.tmp.$$"
  awk -v s="$START_MARK" -v e="$END_MARK" '
    $0 == s { inblock=1; next }
    $0 == e { inblock=0; next }
    !inblock { print }
  ' "$target" > "$tmp" && mv "$tmp" "$target"
}

# status_marked <target> <agent>
status_marked() {
  target="$1"
  agent="$2"
  if [ ! -f "$target" ]; then
    printf '%s: not installed (target absent: %s)\n' "$agent" "$target"
    return 0
  fi
  if has_markers "$target"; then
    printf '%s: installed (markers present in %s)\n' "$agent" "$target"
  else
    printf '%s: not installed (target exists, no markers in %s)\n' "$agent" "$target"
  fi
}

install_claude() {
  mkdir -p "$(dirname "$claude_flag")"
  : > "$claude_flag"
}

uninstall_claude() {
  rm -f "$claude_flag"
}

status_claude() {
  if [ -f "$claude_flag" ]; then
    printf 'claude: installed (flag present: %s)\n' "$claude_flag"
  else
    printf 'claude: not installed (flag absent: %s)\n' "$claude_flag"
  fi
}

# --- Dispatch ---
cmd="${1:-}"
[ $# -gt 0 ] && shift
agent="${1:-codex}"

case "$agent" in
  claude|codex|antigravity) ;;
  *) usage; exit 2 ;;
esac

case "$cmd" in
  install)
    case "$agent" in
      codex)        install_marked "$codex_target" "$carriers_dir/codex.md" ;;
      antigravity)  install_marked "$antigravity_target" "$carriers_dir/antigravity.md" ;;
      claude)       install_claude ;;
    esac
    ;;
  uninstall)
    case "$agent" in
      codex)        uninstall_marked "$codex_target" ;;
      antigravity)  uninstall_marked "$antigravity_target" ;;
      claude)       uninstall_claude ;;
    esac
    ;;
  status)
    case "$agent" in
      codex)        status_marked "$codex_target" "codex" ;;
      antigravity)  status_marked "$antigravity_target" "antigravity" ;;
      claude)       status_claude ;;
    esac
    ;;
  *) usage; exit 2 ;;
esac