# Default checks

Use these checks only when the repository defines none. Run a linter only when the
repository has its configuration file. At a closeout, limit each command to the changed
packages when the tool allows it, for example `go test ./internal/report/...`.

| Language | Format | Static analysis | Types | Tests |
|---|---|---|---|---|
| Go | `gofmt -l .` prints nothing | `go vet ./...`, and `staticcheck ./...` or `golangci-lint run` when configured | The compiler | `go test ./...`, with `-race` when the change touches goroutines, channels or shared state |
| TypeScript | `prettier --check .` when configured | `eslint .` when configured | `tsc --noEmit` | The `test` script |
| Rust | `cargo fmt --check` | `cargo clippy -- -D warnings` | The compiler | `cargo test` |
| Python | `ruff format --check` when configured | `ruff check` when configured | `mypy` when configured | `pytest` |
| SQL migrations | None | The migration linter, or the runner in check mode | None | Apply the migration from the previous version on an isolated database |

Rules for all languages:

- A check that the repository configures has priority over a default in this table.
- A default check that fails on code that you did not change is a finding about the
  base. Report it. Do not fix it in this change.
- Report each default check that you did not run, with the reason.
