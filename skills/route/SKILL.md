---
name: route
description: Use before acting on any request that will change a repo, or that asks for a design decision, debugging help, or planning — decides which skill (or no skill) handles it next.
---

# route

Runs before action on any substantive request. Trivial talk (greetings, questions about
galdr itself) does not need routing.

Announce the destination in one line, then act:

```
routing: <destination> — <one-line reason>
```

Examples:

```
routing: debug — unexpected behavior reported (SSE handler dropping events)
routing: tdd-fast-path — single file, existing coverage, no cross-repo/registry/i18n/migration surface
```

## Decision table

| Signal | Route |
|---|---|
| Question / discussion / no repo mutation | answer directly, no ceremony |
| Bug or unexpected behavior reported | debug |
| Fast path: single file, existing test coverage, no cross-repo / registry / i18n / migration surface | tdd directly (announce "fast path") |
| Feature or change, spec/plan already exists | plan (if plan missing) or waves (if plan exists) |
| Feature, no spec, requirements clear enough to state | shape in synthesis mode → spec without interview |
| Feature, requirements fuzzy, user has a position to test | shape in grill mode |
| Feature, open-ended, no position yet | shape in explore mode |
| Multi-session fog (no spec possible yet) | shape with wayfinder map reference |
| Architecture pain, no specific feature | rearchitect |
| Design question answerable by building | prototype |

Canonical route names, in table order (the exact tokens other skills and the accuracy
tests use): `answer`, `debug`, `tdd-fast-path`, `plan` / `waves`, `shape-synthesis`,
`shape-grill`, `shape-explore`, `shape-wayfinder`, `rearchitect`, `prototype`.

## Fast-path criteria

Route to `tdd-fast-path` only when ALL of these hold:

- Single file changes.
- Existing test coverage already covers the code being touched.

And NONE of these apply:

- Cross-repo: the change spans more than one repo in the workspace, or touches a
  documented mirror pair (two artifacts required to stay in sync across repos — the
  repo's setup config lists which ones).
- Registry or enum surface: adds or changes a closed-enum entry (business type, Catalog
  vertical, and similar).
- i18n catalog surface: adds or changes user-facing strings that need EN + ID.
- Migration surface: adds or changes a schema migration.

If any one of these applies, or the file lacks existing test coverage, route to `plan`
(or `waves` if a plan already exists) instead — the change still needs the normal
ceremony. One boundary: this plan-exit is for changes that are already fully specified
and merely excluded from the fast path. Feature-sized work with no spec still goes
through shape first — the decision table's spec-first rows govern feature scale.

A repo's setup config (`docs/agents/galdr.md`) may override these criteria. Follow the
repo's override when one is configured; use the list above by default.

## Override rule

One word from the user wins. If the user names a different skill or route, switch
immediately. Do not re-litigate the router's own call.

## Output budget

On trivial turns (`answer`, `tdd-fast-path`), the router's own output is at most 2 lines:
the announce line, plus at most one line leading into the answer or the first test. No
extra framing, no re-explaining the decision table.

## Fast path still obeys the Iron Laws

`tdd-fast-path` skips planning ceremony, not discipline. The Iron Laws still apply in
full: write the failing test first, verify completion with fresh evidence, find the root
cause of any fix. "Fast path" names a shorter path to `tdd`, not an exemption from it.
