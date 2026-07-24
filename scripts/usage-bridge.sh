#!/usr/bin/env bash
# galdr usage-bridge: a statusLine wrapper that caches the official rate_limits
# for agent sessions, then delegates to the user's original statusLine command
# (or renders a minimal status if none is saved). Never errors, never blocks.
set -u

# `status`: report installed/cache/original state as three fixed lines and exit,
# without ever touching stdin. Any other invocation (including no args) falls
# through unchanged to the statusLine wrapper path below.
if [ "${1:-}" = "status" ]; then
  settings="${GALDR_CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
  status_cache="${GALDR_RATE_LIMITS_CACHE:-$HOME/.claude/rate-limits-cache.json}"
  status_original="${GALDR_ORIGINAL_STATUSLINE:-$HOME/.claude/galdr/original-statusline}"

  cmd=""
  if [ -f "$settings" ]; then
    cmd=$(jq -r '.statusLine.command // empty' "$settings" 2>/dev/null)
  fi
  case "$cmd" in
    *usage-bridge.sh*) printf 'installed: yes\n' ;;
    *) printf 'installed: no\n' ;;
  esac

  if [ -f "$status_cache" ]; then
    cached_at=$(jq -r '.cached_at // empty' "$status_cache" 2>/dev/null)
    cached_at_int="${cached_at%%.*}"
    if printf '%s' "$cached_at_int" | grep -Eq '^[0-9]+$'; then
      age=$(( $(date +%s) - cached_at_int ))
      printf 'cache: present, age %ss (%s)\n' "$age" "$status_cache"
    else
      printf 'cache: present, age unknown (%s)\n' "$status_cache"
    fi
  else
    printf 'cache: absent (%s)\n' "$status_cache"
  fi

  if [ -f "$status_original" ]; then
    printf 'original: saved\n'
  else
    printf 'original: none\n'
  fi

  exit 0
fi

# Read ALL of stdin (the statusLine JSON Claude Code pipes in).
input=$(cat)

cache="${GALDR_RATE_LIMITS_CACHE:-$HOME/.claude/rate-limits-cache.json}"
original="${GALDR_ORIGINAL_STATUSLINE:-$HOME/.claude/galdr/original-statusline}"

# Cache the official rate limits (usage-threshold rule). Only write when present
# so a limit-less render never clobbers a good cache. Atomic write via temp+mv so
# a concurrent render never exposes a half-written cache to the reader.
rl=$(printf '%s' "$input" | jq -c '.rate_limits | select(. != null) | . + {cached_at: now}' 2>/dev/null)
if [ -n "$rl" ]; then
  tmp="${cache}.tmp.$$"
  if printf '%s\n' "$rl" > "$tmp" 2>/dev/null; then
    mv "$tmp" "$cache" 2>/dev/null || rm -f "$tmp" 2>/dev/null
  fi
fi

# Delegate to the user's original statusLine command if one is saved.
orig_cmd=""
if [ -f "$original" ]; then
  orig_cmd=$(cat "$original" 2>/dev/null)
fi
if [ -n "$orig_cmd" ]; then
  printf '%s' "$input" | eval "$orig_cmd"
  exit 0
fi

# No original saved: render a minimal one-line status.
model=$(printf '%s' "$input" | jq -r '.model.display_name // empty' 2>/dev/null)
cwd=$(printf '%s' "$input" | jq -r '.workspace.current_dir // empty' 2>/dev/null)
branch=""
if [ -n "$cwd" ]; then
  branch=$(git -C "$cwd" --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null)
fi
five=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)
seven=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)

out=""
[ -n "$model" ] && out="$model"
if [ -n "$branch" ]; then
  [ -n "$out" ] && out="$out "
  out="${out}${branch}"
fi
if [ -n "$five" ] || [ -n "$seven" ]; then
  [ -n "$out" ] && out="$out "
  out="${out}5h:${five:-0}% 7d:${seven:-0}%"
fi
printf '%s\n' "$out"
exit 0
