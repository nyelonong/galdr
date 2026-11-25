---
name: senpai
description: Obtain fingerprint-bound human approval of a technical plan or the actual working-tree diff with senpai. Use only when the user requests a plan, document or diff review.
---

# senpai review

The gate launches the runtime's review surface, hands it the real working-tree
change, blocks until a human decides, and records an approval bound to exactly
that state. It owns the diff; you never restate it.

## Run it

- Run the gate only when the user requests a review, after the last focused check
  for the unit and before committing it.
- Pass the criterion the user approved for this unit and the repository paths
  the task owns. Scope narrows what the human sees; it never widens it.
- Never summarize, paste, or reconstruct the diff, and never ask a human to
  approve a description of the change. The gate reads the working tree itself.
- Never launch the reviewer yourself, and never drive its UI. The gate is the
  only supported way to reach it.
- Read-only investigation, review, and verification need no gate.

## Who runs it

Your workflow policy decides when a review runs and which agent or model runs
the command. This skill covers using senpai. Wherever it says "runner", read the
agent that runs `senpai review`, whether that is you or a delegated helper.

## Guided diff view

The bundled HTML page opens **Diff** by default and offers **Guided** beside it.
Write a concise guide for every diff review except a single small file; it is a
best-effort enhancement, not a prerequisite for human review. Include inspected before/after
behavior, optional flow labels and whole-file chapters ordered by logic and risk.
Give a chapter `steps` when it changes more than one function: one step per
function or region, `{"title", "note", "repository", "path", "lines": [start, end]}`,
with a title of at most 80 characters, a one-line note, one of the chapter's files
and after-side line numbers (before-side for a deleted file). Each changed line
shows under the first step whose range holds it; changed lines outside every
range show as "Other lines", so cover each function's whole range.
Keep chapter summaries to two sentences; the page shows only their first lines
in the flow. The real complete diff remains authoritative.

Write the guide yourself from the diff you have already inspected. Store guide JSON privately
outside reviewed repositories and the client recovery directory. Obtain the exact
scoped fingerprint with `status --repo ROOT [--paths a,b]` or `status --json
REQUEST`; exit 1 for no approval is normal. Each `(repository, path)` belongs to
one chapter. Preflight the criterion, scope and guide before running the review; preflight
opens no reviewer, changes no ledger and never establishes approval.

If the guide fails preflight, correct it once from the reported error and preflight
again. If it still fails, skip the guide: run without `--guide` with the
same criterion and scope, require plain preflight to pass, and report briefly that
the guide was skipped and why. Repository, scope, permission or other non-guide
failures remain blockers. Pass `--guide PATH` or an inline guide, never both. The
actual review repeats strict validation; a failure after the canonical review is
invoked follows the gate's normal stop/recovery rules, not a guide fallback.

No harness model/network calls are made. Without an authored guide, Guided uses
honestly labeled directory groups. Chapter checkboxes are session-only reading
progress, not decisions or exemptions. Guide-bearing reviews require the bundled
`html` backend; leave existing non-HTML and document flows unchanged.

## Waiting and recovery

Before capture, retain the criterion, exact scope/document, authorized phase and recovery location in supported history or an existing plan. Keep private command records outside the reviewed tree; do not create a plan merely to wait. Your runtime owns the command's handle and the waiting. Keep reviewed inputs unchanged through approval verification and use/consumption; record interim operational state externally. Recover the original command and result before relaunching. Unknown ownership or consequential outcome blocks replay and progression; it never implies approval.

Pass a new or empty private recovery directory outside the
reviewed inputs. Do not prepopulate it; the client creates it with mode 0700 and
files with mode 0600. Existing nonempty directories are refused, never overwritten.
Inspect `request.json`, `process.json`, `state.json`, `stderr.log`, and the running
command before deciding whether a new invocation is safe. Recorded PIDs aid diagnosis;
use your runtime's cancellation, not blind PID-based killing or replay.

Run the client directly as a foreground command with `--recovery-dir PATH`; it
owns the request, process, diagnostic and decision files. Do not write launcher
scripts, PID files, output redirection, process substitution or detached
processes. Give the command a deadline longer than the client's own review
timeout (`TASK_REVIEW_TIMEOUT`, default 1800 seconds). A command still open while
`state.json` says `reviewing` is a human deciding, not a stuck review; check the
recovery files before interrupting it. While it waits, live stderr and
`browser-url.txt` give the review URL. A report from whoever ran the command never
proves approval on its own: check `state.json`, `result.json` and `verify`.

`state.json` distinguishes `starting`, `reviewing`, `finished`, and `error`.
`finished` includes the human decision and exit code: exit 1 with
`request-changes`, `return-to-planning`, or `cancelled` is not a launcher failure.
`result.json` exists only after protocol, decision and ledger checks succeed;
approval additionally requires unchanged reviewed inputs. Read `browser-url.txt`
while waiting; it is withdrawn on normal
completion, while the URL remains in `stderr.log`. Error state or missing result
never grants approval. Recovery artifacts do not replace parent verification.

## Act on the decision

The command exits 0 only for `approve`.

- `approve` — continue; `verify` must still pass at commit time.
- `request-changes` — apply the annotations in scope, rerun focused checks, and
  gate the corrected state again.
- `return-to-planning` — the criterion was wrong, not the code. Stop, return to
  planning with the user, and re-approve before further work.
- `cancelled` — the human withdrew. Stop.

Every other outcome is an error: a failed reviewer, a malformed result, a
timeout, or a repository state that changed under the reviewer. Report it and
stop. Never route around a failed gate.

## Reviewers

The gate speaks one protocol, so the surface is a choice, not a branch. It opens
the bundled HTML page by default. `TASK_REVIEW_REVIEWER=rdg` sends the identical
request to RDG, which reviews inside a running editor window; the repository must
be open there and the root must be a canonical absolute path. The README records
a known RDG failure, so keep the HTML page unless told otherwise. Choose the supported surface before launch, never mid-decision: one human decision
for the captured state.

## Commit

- Run `verify` immediately before staging. Any change to the reviewed paths since
  approval fails it; that failure is real and must be re-reviewed, not waived.
- Run `consume` after the commit lands, so the approval cannot cover a second
  commit.
- A correction after approval invalidates it. A passing test suite does not
  renew an approval. Executable evidence follows your workflow's freshness
  contract; approval alone is not a reason to rerun it.

## Technical-plan documents

Present the single technical plan through the document gate. Its approval
authorizes the listed implementation scope directly, not a second planning phase:

```sh
senpai review-doc --criterion "<the question this document must answer>" --doc <path>
senpai verify-doc --doc <path>
senpai consume-doc --doc <path>
```

The page renders the document as a document: headings, paragraphs, tables and
code, with a heading outline in the sidebar. A comment names the **source range**
of the block it was written on, so a comment on a paragraph spanning lines 5-7
comes back as `start_line: 5, end_line: 7` and the agent edits the right place.
Fenced code is tokenized only when the fence names a language the reviewer
handles; anything else stays plain.

Apply the returned annotations, edit the document, and run `review-doc` again:
the approval is bound to a fingerprint of the exact text, so an edit after
approval invalidates it.

- `request-changes` — revise the document against every comment, then re-review.
- `return-to-planning` — the premise is wrong, not the prose. Stop and return.
- `approve` — the document is approved as written; `consume-doc` retires the
  approval once the next phase has used it.
- `cancelled` — the human withdrew. Stop.

When requested, this is the pre-implementation document approval used by your planning step. Do not add a
separate specification gate, mandatory walkthrough or competing chat confirmation.
If the page cannot be opened, report the failure and stop. No automatic unbound
chat fallback is permitted; a supported replacement requires explicit authorization.

## Commands

The client is the installed `senpai` binary, never a script in the repository under review. Call it by its absolute path (usually `~/.local/bin/senpai` or `~/.cargo/bin/senpai`, expanded; `command -v senpai` finds it); `senpai` below means that path.

- `review --criterion TEXT --repo ROOT [--paths a,b] [--base REF [--head REF] | --pr N] --recovery-dir PATH`
  opens the review, retains client-owned artifacts, and waits for a human decision.
- `review-doc --criterion TEXT --doc PATH --recovery-dir PATH` does the same for
  the technical plan.
- `preflight --criterion TEXT --repo ROOT [--paths a,b] [--base REF [--head REF] | --pr N] [--guide PATH]`
  checks inputs without opening a review or changing an approval.
- `verify --repo ROOT [--paths a,b] [--base REF [--head REF] | --pr N]` checks the recorded
  approval against the current tree.
- `consume --repo ROOT [--base REF [--head REF] | --pr N]` retires the approval after the commit.

By default a review covers uncommitted changes against `HEAD`. `--base REF`
covers everything since the merge base with `REF`, committed and uncommitted,
as a pull request diff does. Adding `--head REF` reviews that commit range
alone; the working tree is ignored. Both need a single `--repo`. Pass the same
range flags to every later command. An approval is bound to the resolved merge
base, head commit and content, not to the ref names: a ref that moves so either
commit changes no longer verifies.

`--pr N` (or a pull request URL) reviews a GitHub pull request: `gh pr view`
gives its base and head commits, which are reviewed as a commit range, and the
page shows the title, description and commits as context. Both commits must
already be local; if one is missing the command stops with the `git fetch` to
run. Every later command asks `gh` again, so a push to the pull request stops
`verify` passing, and a failing or missing `gh` fails the command closed.
senpai never fetches, comments or approves on GitHub. GitHub reports the base branch's current
tip, so a push to the base branch also needs a fetch before `verify` passes.
If `gh` is offline, `revoke --repo ROOT` without `--pr` still retires the
approval. Range and pull request reviews need the bundled HTML reviewer.

The bundled HTML reviewer puts every review in one local inbox that `senpai`
starts on demand; the client still blocks and returns the same result. An
interrupted, timed-out or killed client withdraws its item, and a stopped or
crashed inbox fails the review closed (exit 2). `senpai inbox` reopens the page;
`SENPAI_INBOX=0` gives a review its own one-off page instead. Inside Tern, a new
review opens the page in a browser block beside the agent's pane; inside Rex,
a split there shows the page through terminal-browser, or `senpai tui` without it; `SENPAI_SURFACE=browser` keeps the browser.
The terminal-browser split is the default inside Rex and needs no setting; when
terminal-browser is not on `PATH`, `SENPAI_TERMINAL_BROWSER` names its path.

The reviewer is any process that takes one JSON request argument and prints one
JSON result line. `TASK_REVIEW_REVIEWER` selects it and defaults to the bundled
HTML page; `RDG_CONTROL_COMMAND` is still honored when it is unset. When `rdg` is
the reviewer, the repository must already be open in the
running application, and every repository root must be a canonical absolute
path — the client realpaths it, so a symlinked path such as `/tmp/x` is
rejected while `/private/tmp/x` is accepted.
