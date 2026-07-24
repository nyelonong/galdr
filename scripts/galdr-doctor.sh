#!/usr/bin/env bash
# galdr-doctor: diagnoses galdr's wiring (hook enablement, registration, live
# emission, version sync, usage-bridge, per-repo config) in one run. Never
# mutates anything: fixes are suggested as commands in the detail text, never
# executed.
#
# Usage: galdr-doctor.sh [repo-dir] [--home <dir>] [--plugin-root <dir>]
#   repo-dir       default: cwd
#   --home         default: $HOME
#   --plugin-root  default: this script's own parent-of-scripts/ directory
set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
default_plugin_root="$(cd "$script_dir/.." && pwd)"

repo_dir="$(pwd)"
home_dir="${HOME:-}"
plugin_root="$default_plugin_root"
repo_dir_set=0

while [ $# -gt 0 ]; do
  case "$1" in
    --home)
      home_dir="$2"
      shift 2
      ;;
    --plugin-root)
      plugin_root="$2"
      shift 2
      ;;
    *)
      if [ "$repo_dir_set" -eq 0 ]; then
        repo_dir="$1"
        repo_dir_set=1
      fi
      shift
      ;;
  esac
done

tmp_emit=$(mktemp)
cleanup() { rm -f "$tmp_emit"; }
trap cleanup EXIT

ok_count=0
advise_count=0
fail_count=0
na_count=0

# report <check> <result> <detail...>
report() {
  check_name="$1"
  result="$2"
  shift 2
  detail="$*"
  printf 'DOCTOR %s %s %s\n' "$check_name" "$result" "$detail"
  case "$result" in
    OK) ok_count=$((ok_count + 1)) ;;
    ADVISE) advise_count=$((advise_count + 1)) ;;
    FAIL) fail_count=$((fail_count + 1)) ;;
    N/A) na_count=$((na_count + 1)) ;;
  esac
}

# Check 1: enabled-flag. Stable path survives plugin updates; legacy in-plugin
# flag is still honored (see hooks/session-start).
stable_flag="$home_dir/.claude/galdr/enabled"
legacy_flag="$plugin_root/hooks/enabled"
flag_present=0
if [ -f "$stable_flag" ]; then
  flag_present=1
  report enabled-flag OK "stable flag present ($stable_flag)"
elif [ -f "$legacy_flag" ]; then
  flag_present=1
  report enabled-flag OK "legacy flag present ($legacy_flag)"
else
  report enabled-flag FAIL "no enabled flag found; run: mkdir -p \"$home_dir/.claude/galdr\" && touch \"$stable_flag\""
fi

# Check 2: hook-registered. hooks.json must wire session-start on the
# startup|clear|compact matcher, and the script itself must be executable.
hooks_json="$plugin_root/hooks/hooks.json"
session_start="$plugin_root/hooks/session-start"
if [ ! -f "$hooks_json" ]; then
  report hook-registered FAIL "missing hooks/hooks.json"
elif ! grep -q "session-start" "$hooks_json"; then
  report hook-registered FAIL "hooks/hooks.json does not reference session-start"
elif ! grep -qF 'startup|clear|compact' "$hooks_json"; then
  report hook-registered FAIL "hooks/hooks.json matcher is not startup|clear|compact"
elif [ ! -x "$session_start" ]; then
  report hook-registered FAIL "hooks/session-start is not executable; run: chmod +x \"$session_start\""
else
  report hook-registered OK "session-start registered on startup|clear|compact and executable"
fi

# Check 3: emission. Run session-start with HOME=home_dir; when the flag is
# present the output must byte-equal hooks/bootstrap.md, when absent it must
# be empty. Compared via cmp (not command substitution) so trailing bytes
# count.
: > "$tmp_emit"
HOME="$home_dir" bash "$session_start" > "$tmp_emit" 2>/dev/null
if [ "$flag_present" -eq 1 ]; then
  if cmp -s "$tmp_emit" "$plugin_root/hooks/bootstrap.md"; then
    report emission OK "output byte-equals hooks/bootstrap.md"
  else
    report emission FAIL "session-start output does not match hooks/bootstrap.md"
  fi
else
  if [ -s "$tmp_emit" ]; then
    report emission FAIL "flag absent but session-start emitted output"
  else
    report emission OK "flag absent, emission correctly empty"
  fi
fi

# Check 4: version. Only meaningful when plugin_root is an installed
# marketplace cache dir shaped .../cache/<owner>/<name>/<ver>/ -- compare
# <ver> to the plugin.json version at that same root. A dev checkout (any
# other shape) ADVISEs with that situation, never a false FAIL.
norm_root="${plugin_root%/}"
cache_ver="$(basename "$norm_root")"
name_dir="$(dirname "$norm_root")"
owner_dir="$(dirname "$name_dir")"
cache_dir="$(dirname "$owner_dir")"
if [ "$(basename "$cache_dir")" = "cache" ]; then
  plugin_json="$plugin_root/.claude-plugin/plugin.json"
  if [ -f "$plugin_json" ]; then
    pj_ver=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$plugin_json" | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
    if [ "$cache_ver" = "$pj_ver" ]; then
      report version OK "cache version $cache_ver matches plugin.json"
    else
      report version ADVISE "cache version $cache_ver != plugin.json version $pj_ver; re-sync the plugin (reinstall/update galdr)"
    fi
  else
    report version ADVISE "cache path detected ($cache_ver) but .claude-plugin/plugin.json missing; re-sync the plugin"
  fi
else
  report version ADVISE "not a cache path (dev checkout): $plugin_root"
fi

# Check 5: usage-bridge. Delegates to scripts/usage-bridge.sh status if the
# script is shipped; stdin is /dev/null so it can never block on a tty. Empty
# output means no statusline context to report on (e.g. a non-Claude host,
# or the bridge not installed there) -> N/A, never FAIL.
bridge="$plugin_root/scripts/usage-bridge.sh"
if [ ! -f "$bridge" ]; then
  report usage-bridge N/A "no scripts/usage-bridge.sh in this plugin root"
else
  bridge_out=$(bash "$bridge" status < /dev/null 2>/dev/null)
  bridge_rc=$?
  if [ "$bridge_rc" -ne 0 ]; then
    report usage-bridge ADVISE "usage-bridge.sh status exited $bridge_rc; run: /galdr:usage-bridge status"
  elif [ -z "$bridge_out" ]; then
    report usage-bridge N/A "no statusline context (non-Claude host or bridge not installed)"
  elif printf '%s' "$bridge_out" | grep -qi 'installed: yes'; then
    report usage-bridge OK "$bridge_out"
  elif printf '%s' "$bridge_out" | grep -qi 'installed: no\|not installed'; then
    report usage-bridge ADVISE "$bridge_out; run: /galdr:usage-bridge install"
  else
    report usage-bridge OK "$bridge_out"
  fi
fi

# Check 6: repo-config. Per-repo galdr config that verify/waves/review/branches
# read for gate commands, invariants, model tiers, and smoke details.
if [ -f "$repo_dir/docs/agents/galdr.md" ]; then
  report repo-config OK "docs/agents/galdr.md present"
else
  report repo-config ADVISE "docs/agents/galdr.md missing; run: /galdr:setup"
fi

printf 'DOCTOR summary: %d OK, %d ADVISE, %d FAIL, %d N/A\n' \
  "$ok_count" "$advise_count" "$fail_count" "$na_count"

if [ "$fail_count" -gt 0 ]; then
  exit 1
fi
exit 0
