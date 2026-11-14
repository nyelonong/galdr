# Browser approval gate

A local page shows the human the real working-tree change and records an approval
bound to exactly that state. Run it only when the user asks. It needs `python3` (3.9
or newer) and a git repository; the client is `scripts/task_review.py` in this skill's
directory, never a script inside the repo under review.

## Diff

1. After the last focused check and before committing, run:

   ```sh
   python3 <skill dir>/scripts/task_review.py review --criterion "<what the user approved this change to do>" --repo <repo root> [--paths a,b] --recovery-dir <new directory outside the repo>
   ```

2. It opens the page and blocks until the human decides; the URL is in
   `<recovery dir>/browser-url.txt` and on stderr. Never paste or summarize the diff for
   approval, and never drive the page yourself. `TASK_REVIEW_TIMEOUT` (default 1800
   seconds) bounds the wait.
3. Act on the exit:
   - `approve` (exit 0): continue.
   - `request-changes`: apply the annotations in scope, rerun the focused checks, run
     the gate again.
   - `return-to-planning`: the criterion was wrong; stop and go back to the plan.
   - `cancelled`: stop.
   - anything else (timeout, malformed result, tree changed during review): report it
     and stop. Never route around a failed gate.
4. Run `verify --repo <root> [--paths a,b]` right before staging; any change since
   approval fails it, and that failure needs a new review. Run `consume --repo <root>`
   after the commit so one approval never covers two commits.

An optional guide (`--guide <json outside the repo>`) adds a guided view; check it
first with `preflight` and the same arguments. If it fails twice, review without it.

## Plan document

```sh
python3 <skill dir>/scripts/task_review.py review-doc --criterion "<the question the document must answer>" --doc <path> --recovery-dir <new directory>
python3 <skill dir>/scripts/task_review.py verify-doc --doc <path>
python3 <skill dir>/scripts/task_review.py consume-doc --doc <path>
```

Comments come back with source line ranges; revise and run `review-doc` again, since an
edit after approval voids it.

The recovery directory must be new or empty; the client creates it privately and
refuses to overwrite one. Approvals are recorded in the repository's git directory
(`task-review-approval.jsonl`).
