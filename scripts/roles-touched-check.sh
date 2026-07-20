#!/usr/bin/env bash
# galdr roles-touched-check: scans a repo's specs for role names (from
# docs/agents/roles-and-journeys.md) that appear in a spec's prose body but
# are missing from its **Roles touched:** field. A presence check, not a
# semantic one.
#
# Usage: roles-touched-check.sh [spec-file-or-dir...]
#   no args:      checks docs/specs/*.md, relative to the current working directory
#   file args:    checks exactly those files
#   directory args: checks *.md directly under that directory
#   args may mix files and directories
#
# If docs/agents/roles-and-journeys.md does not exist (relative to the
# current working directory), exits 0 immediately: nothing to check yet.
#
# SHA-range mode (checking only specs changed in a git range) is deferred —
# out of scope for this presence-only backstop; see docs/backlog.md.
set -u

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

# Determine files to check. Args may be files or directories; directories
# expand to the *.md files directly under them.
files=()
if [ "$#" -gt 0 ]; then
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
