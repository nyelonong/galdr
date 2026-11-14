# Browser approval gate

A local page shows the human the real working-tree change. The gate records an approval
for exactly that state. Run it only when the user asks. It needs `python3` (3.9 or
newer) and a git repository. The client is `scripts/task_review.py` in the folder of
this skill. Never use a script from the repository under review.

## Diff

1. After the last focused check and before the commit, run:

   ```sh
   python3 <skill dir>/scripts/task_review.py review --criterion "<what the user approved this change to do>" --repo <repo root> [--paths a,b] --recovery-dir <new directory outside the repo>
   ```

2. The page opens and the command waits for the human decision. The URL is in
   `<recovery dir>/browser-url.txt` and on stderr. Never paste or summarize the diff for
   approval. Never operate the page yourself. `TASK_REVIEW_TIMEOUT` (default 1800
   seconds) sets the longest wait.
3. Act on the result:
   - `approve` (exit 0): continue.
   - `request-changes`: apply the annotations in scope, run the focused checks again,
     and run the gate again.
   - `return-to-planning`: the criterion was wrong. Stop and go back to the plan.
   - `cancelled`: stop.
   - Any other result (timeout, bad result, tree changed during the review): report it
     and stop. Never go around a failed gate.
4. Run `verify --repo <root> [--paths a,b]` immediately before the commit. A change
   after the approval makes it fail, and that failure needs a new review. Run
   `consume --repo <root>` after the commit. Then one approval never covers two commits.

An optional guide (`--guide <json outside the repo>`) adds a guided view. If it fails
`preflight` two times, review without it.

## Plan document

```sh
python3 <skill dir>/scripts/task_review.py review-doc --criterion "<the question the document must answer>" --doc <path> --recovery-dir <new directory>
python3 <skill dir>/scripts/task_review.py verify-doc --doc <path>
python3 <skill dir>/scripts/task_review.py consume-doc --doc <path>
```

Each comment comes back with its source line range. Change the document and run
`review-doc` again. An edit after the approval cancels it.

The recovery directory must be new or empty. The client makes it private and does not
overwrite an existing one.
