# roles-and-journeys.md: the interview, the citation rule, and the output contract

Full procedure for `setup`'s step 5 — the interview that produces the target repo's
`docs/agents/roles-and-journeys.md`. `SKILL.md` names the trigger; this file holds the
steps. Content comes only from what this run finds in the *target* repo — never a
project name, role name, or domain term hardcoded here.

## a. Read first, interview only for gaps

Before asking the user anything, read the target repo's specs, other docs, and code for
domain roles: who/what acts on the system, what each can do, what lifecycle states each
touches, its end-to-end journey, and its hard boundaries. Draft a role entry from what's
found. Interview the user only for the fields that draft left empty — a role fully
documented already needs zero questions. Ask one role at a time; show the draft first so
the user is confirming or filling gaps, not dictating from scratch. Once every role is
drafted and confirmed, assemble the full `roles-and-journeys.md` content and show it in
full — the same recommend-then-confirm shape as `SKILL.md`'s steps 2-3 — before writing
anything to disk.

## b. Fixed output contract

Each role is an `## <RoleName>` heading. Directly under it, in this order, bolded
lead-in lines with no further nesting: `**Identity:**`, `**Capabilities:**`,
`**Lifecycle states touched:**`, `**Journey:**`, `**Boundaries:**`, `**Status:**`
(`Built` or `Future/unbuilt — <condition>, not yet implemented`), and an optional
`**Owner:**` (see e below). Every claim on every line ends with a citation: `path:line`
for code,
`path#heading` for docs. A trailing `## Cross-role boundaries` heading holds gates or
invariants that span more than one role (a shared publish gate, for example) — write it
only if at least one such boundary exists. A trailing `## Changelog` heading holds one
line per write or refresh (see f).

## c. Unsourced-claim rule

A claim with no existing written source — not in the repo's docs, not in its code — is
never written into the file, sourced or not, even if the user states it confidently
during the interview. Note it instead as an open gap: name the role and field, and point
at `shape` as the next step to spec and settle it. Continue drafting the rest of that
role and any other roles; one open gap does not block the whole write.

## d. Zero-roles case

If detection plus interview together find no domain roles at all (a pure-tooling or
library repo, for instance), do not write an empty file. Report "no domain roles
detected — skipping roles-and-journeys.md" and stop step 5 there.

## e. Owner field sourcing

`**Owner:**` is populated only from an existing sourced document — a CODEOWNERS file, an
ownership doc — cited the same as any other claim. When no such source exists, omit the
`**Owner:**` line entirely; never leave it blank and never fill it from an unsourced
interview answer.

## f. Changelog append

Every write or refresh appends exactly one line to the trailing `## Changelog` heading,
prior lines untouched: `- YYYY-MM-DD — <role or "doc-wide"> — <what/why>`. A fresh write
produces the file's first entry; a refresh appends one more.

## g. Scoped refresh trigger

An ordinary re-run of `setup` (file already present) leaves `roles-and-journeys.md`
untouched — step 5 is skipped entirely unless the user explicitly asks for a refresh.
When a refresh is asked for:

- **Named role** ("refresh just Merchant") — re-run the read-first-then-interview
  procedure for that role's section only; show the redrafted section and get
  confirmation before writing, same diff-before-overwrite pattern as the full-file
  case; the rest of the file stays byte-identical except for the one new Changelog line.
- **No role named** — full-file refresh, still gated by `SKILL.md`'s existing
  Human-edits diff-before-overwrite pattern: show the diff, get confirmation, before
  overwriting.

## h. Review-sources auto-registration

On the *first* successful write only, add a line for `docs/agents/roles-and-journeys.md`
under the target repo's own `## Review sources` section in `docs/agents/galdr.md` — no
separate step, no separate skill invocation. A later refresh does not duplicate this
line; check it's already there before adding.

## i. CI-Gate offer

Once `docs/agents/roles-and-journeys.md` exists (right after the first write, or when
step 5 is skipped on a repo that already has the file), offer to add
`bash scripts/roles-touched-check.sh` to the target repo's `## Gates` section in
`docs/agents/galdr.md` — same accept/decline pattern as setup's other detected Gate
defaults. The script exits 0/1 and takes an optional list of spec files and/or
directories (`bash scripts/roles-touched-check.sh [spec-file-or-dir...]`, defaulting to
`docs/specs/*.md` with no args), or a git revision range instead
(`bash scripts/roles-touched-check.sh --range <rev-range>`, scoped to specs changed
within that range, excluding deletions); it checks presence only (a spec naming a role
in prose but not in its "Roles touched" field), never meaning — a contradiction between
a spec's claim and the doc is `shape`'s job, not this script's.
