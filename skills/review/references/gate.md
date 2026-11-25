# Browser approval gate

A local page shows the human the real working-tree change. The gate records an approval
for exactly that state. Run it when the user asks, or when galdr chooses the Gate
commit route. It needs a git repository.

## Client

Choose the client one time for each unit, before the first gate command:

1. Run `command -v senpai`. If it shows a path, resolve it and `<repo root>` with
   `realpath`. If the result is an absolute path outside the resolved root, the client
   is that path.
2. If it shows no path, or the result is not absolute, or the result is inside
   `<repo root>`, the client is `python3 <skill dir>/scripts/task_review.py`. It
   needs `python3` 3.9 or newer. `<skill dir>` is the `review` skill folder.

Use the same client for all gate commands of one unit or one document. Never use a client
from the repository under review. `<client>` below is the client that you chose. Tell the
user which client you chose and why. Inside galdr, this file sets when the gate runs and
which client it uses, also when the `senpai` skill is loaded.

## Diff

1. After the last focused check and before the commit, run:

   ```sh
   <client> review --criterion "<what the user approved this change to do>" --repo <repo root> [--paths a,b] --recovery-dir <new directory outside the repo>
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
4. Run `<client> verify --repo <root> [--paths a,b]` immediately before the commit. A change
   after the approval makes it fail, and that failure needs a new review. Run
   `<client> consume --repo <root>` after the commit. Then one approval never covers two commits.

An optional guide (`--guide <json outside the repo>`) adds a guided view. If it fails
`<client> preflight` two times, review without it.

## Plan document

```sh
<client> review-doc --criterion "<the question the document must answer>" --doc <path> --recovery-dir <new directory>
<client> verify-doc --doc <path>
<client> consume-doc --doc <path>
```

Each comment comes back with its source line range. Change the document and run
`review-doc` again. An edit after the approval cancels it.

The recovery directory must be new or empty. The client makes it private and does not
overwrite an existing one.
