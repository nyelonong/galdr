# Progress and usage: cache reader, staleness, report layout

Detailed recipes for the rate-limit reader, its staleness and fallback logic, and the
gate/run-end usage report. The `waves/SKILL.md` body summarizes these; this file holds
the exact steps. All config keys named here live in the `## Budget` section of
`docs/agents/galdr.md` (written by setup) — read them from there, never hardcode a value.

## Rate-limit cache read

1. Resolve the file path from the `rate-limits-cache` key (default
   `~/.claude/rate-limits-cache.json`). The statusline writes this file on its own
   cadence; galdr only reads it and never queries any usage API.
2. Read the file and parse these fields:
   - `five_hour.used_percentage` — integer/float percent of the 5-hour window used.
   - `seven_day.used_percentage` — same for the 7-day window.
   - `resets_at` — when the 5-hour window resets (used in the report).
   - `cached_at` — when the statusline last wrote the file (used for staleness).
3. Compute staleness: `now - cached_at`. Compare against the `rate-limits-max-age` key
   (default `300`, in seconds).

## Unavailable — the fallback rule

Treat the rate-limit data as **unavailable** whenever any of these hold:

- The file at `rate-limits-cache` does not exist.
- The file exists but cannot be read or parsed (bad JSON, missing fields).
- `now - cached_at` is greater than `rate-limits-max-age` seconds (the cache is stale).

When unavailable, waves never errors and never blocks the run. Concretely:

- The **usage report** drops the limit percentages and prints tokens only, plus the line
  `for your limit %, run /usage`.
- The **quota-threshold trigger** in the budget guard is inactive — it cannot fire
  without fresh percentages. The guard's other triggers (usage limit warning, "park it")
  still apply unchanged.

Availability is decided per read, not once per run — a cache that was stale at one wave
gate may be fresh at the next.

## Usage and token report layout

Emitted at every wave gate and once more at run end.

When the cache is available:

```
Usage — wave <N>
  tokens: <this wave> (cumulative <running total>)
  5h limit: <five_hour.used_percentage>%  (resets <resets_at>)
  7d limit: <seven_day.used_percentage>%
```

When the cache is unavailable:

```
Usage — wave <N>
  tokens: <this wave> (cumulative <running total>)
  for your limit %, run /usage
```

Rules:

- **Token source by mode.** In Workflow-tool mode, take per-wave tokens from the wave's
  workflow-completion `subagent_tokens`. In Agent-tool mode, sum the usage reported by
  each Agent return in the wave. Cumulative is the running sum across all waves so far.
- **Percentages are usage limits, not cost.** Label them as limit percentages; never
  present them as a dollar figure.
- **Reset time** is shown only on the 5h line, taken from `resets_at`.
- At run end, print the same block with the final wave number and the final cumulative
  token total.
