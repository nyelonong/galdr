# Out of scope

Each entry: what was proposed or removed, and why it stays out. Reopen one only with a
session that shows the failure it would have prevented (see `SCOPE.md`).

| Idea | Why it stays out |
|---|---|
| An always-on session hook | It cost context in every session and forced routing on small talk. tdd, verify and debug load by description when they apply. |
| An automatic router skill | `/galdr` picks a playbook when called; the user is the router the rest of the time. |
| A separate council skill | One independent read-only reviewer in `review` covers the need without four extra agents. |
| Model-tier and usage-limit machinery | Runtimes already pick models and show usage; galdr duplicated them and broke when they changed. |
| Durable memory files beside the plan | The plan file holds status, evidence and `next:`; a second ledger drifted from it. |
| Native Codex and Antigravity carriers | They shipped broken for months; `npx skills add` installs the same skills. |
| A per-repo galdr config file | Repo commands belong in the repo's own `CLAUDE.md` or `AGENTS.md`. |
| A backlog, retro or doctor skill | Issue trackers, the plan file and `git log` already do these jobs. |
| Runtime-specific mechanics (Pi, Codex or omp adapters, a fixed model for the review gate, a named language skill such as one for Go) | galdr is generic. It loads the installed skill for a language and uses the runtime's own tools. |
| A frozen list of when independent review is mandatory | galdr decides from the defect that a change can cause. A fixed list turns that judgment into a checklist. |
