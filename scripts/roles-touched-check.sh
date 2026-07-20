#!/usr/bin/env bash
# galdr roles-touched-check: scans a repo's specs for role names (from
# docs/agents/roles-and-journeys.md) that appear in a spec's prose body but
# are missing from its **Roles touched:** field. A presence check, not a
# semantic one.
#
# Usage: roles-touched-check.sh [spec-file-or-dir...]
#        roles-touched-check.sh --range <rev-range>
#   no args:      checks docs/specs/*.md, relative to the current working directory
#   file args:    checks exactly those files
#   directory args: checks *.md directly under that directory
#   args may mix files and directories
#   --range <rev-range>: checks only docs/specs/*.md files changed within that git
#     revision range (e.g. `HEAD~3..HEAD`, any `git diff`-accepted range), excluding
#     files deleted within the range. Mutually exclusive with file/dir args. Must run
#     inside a git repo; an invalid range or non-git directory exits 2 (usage/execution
#     error, distinct from the 0/1 flag-result codes below).
#
# If docs/agents/roles-and-journeys.md does not exist (relative to the
# current working directory), exits 0 immediately: nothing to check yet.
set -u

range=""
if [ "${1:-}" = "--range" ]; then
  if [ "$#" -ne 2 ]; then
    echo "usage: $0 --range <rev-range>  (no other args allowed with --range)" >&2
    exit 2
  fi
  range="$2"
  shift 2
elif printf '%s\n' "$@" | grep -qx -- '--range'; then
  echo "usage: --range must be the only argument, given as: $0 --range <rev-range>" >&2
  exit 2
fi

roles_file="docs/agents/roles-and-journeys.md"

if [ ! -f "$roles_file" ]; then
  printf 'nothing to check yet (no %s)\n' "$roles_file"
  exit 0
fi

# Extract role names from '## <RoleName>' headings, skipping the two headings
# in this file that are not roles.
roles=$(awk '
  /^## / {
    name = $0
    sub(/^## /, "", name)
    sub(/[[:space:]]+$/, "", name)
    if (name == "Cross-role boundaries" || name == "Changelog") next
    print name
  }
' "$roles_file")

if [ -z "$roles" ]; then
  exit 0
fi

# Determine files to check.
files=()
if [ -n "$range" ]; then
  # --range mode: docs/specs/*.md files changed within the range, excluding
  # deletions (diff-filter=d) — nothing to check for a file that's gone.
  changed=$(git diff --name-only --diff-filter=d "$range" -- docs/specs/ 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ]; then
    printf 'invalid range or not a git repo: %s\n' "$changed" >&2
    exit 2
  fi
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    case "$f" in
      *.md) [ -f "$f" ] && files+=("$f") ;;
    esac
  done <<< "$changed"
elif [ "$#" -gt 0 ]; then
  # Args may be files or directories; directories expand to the *.md files
  # directly under them.
  for arg in "$@"; do
    if [ -d "$arg" ]; then
      for f in "$arg"/*.md; do
        [ -e "$f" ] || continue
        files+=("$f")
      done
    else
      files+=("$arg")
    fi
  done
else
  for f in docs/specs/*.md; do
    [ -e "$f" ] || continue
    files+=("$f")
  done
fi

# Escape a string for use inside a POSIX extended regex.
regex_escape() {
  printf '%s' "$1" | sed -e 's/[][\.*^$/+?(){}|]/\\&/g'
}

# True (exit 0) if role name (whole-word, case-insensitive) appears in text.
name_in_text() {
  local text="$1" role="$2" pattern
  pattern=$(regex_escape "$role")
  printf '%s' "$text" | grep -qiE "(^|[^A-Za-z0-9_])${pattern}([^A-Za-z0-9_]|\$)"
}

# True (exit 0) if role name appears as one comma-separated entry in field.
name_in_field() {
  local field="$1" role="$2" part role_lc part_lc
  role_lc=$(printf '%s' "$role" | tr '[:upper:]' '[:lower:]')
  IFS=',' read -ra parts <<< "$field"
  for part in "${parts[@]}"; do
    part_lc=$(printf '%s' "$part" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | tr '[:upper:]' '[:lower:]')
    [ "$part_lc" = "$role_lc" ] && return 0
  done
  return 1
}

flagged=0

for spec in "${files[@]}"; do
  [ -f "$spec" ] || continue

  field=$(grep -m1 -i '^\*\*Roles touched:\*\*' "$spec" | sed -E 's/^\*\*[Rr]oles [Tt]ouched:\*\*[[:space:]]*//')
  body=$(grep -v -i '^\*\*Roles touched:\*\*' "$spec")

  while IFS= read -r role; do
    [ -z "$role" ] && continue
    if name_in_text "$body" "$role"; then
      if ! name_in_field "$field" "$role"; then
        printf '%s: %s\n' "$spec" "$role"
        flagged=1
      fi
    fi
  done <<< "$roles"
done

exit "$flagged"
