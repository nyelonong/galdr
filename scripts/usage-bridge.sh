#!/usr/bin/env bash
# galdr usage-bridge: a statusLine wrapper that caches the official rate_limits
# for agent sessions, then delegates to the user's original statusLine command
# (or renders a minimal status if none is saved). Never errors, never blocks.
set -u

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
