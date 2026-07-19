# TS conventions

Five defaults for TypeScript work under the tdd skill, each with the one-line reason
and a minimal example.

**`satisfies` over `as`** — why: `as` silences the checker; `satisfies` keeps inference
and still checks the shape.
Example: `const config = { retries: 3 } satisfies RetryConfig;`

**`unknown` over `any` at boundaries** — why: `any` disables checking everywhere it
flows; `unknown` forces a narrowing step before use.
Example: `function handle(input: unknown) { if (isValidPayload(input)) { /* typed */ } }`

**Literal unions over enums** — why: enums add a runtime object and awkward interop;
literal unions are plain strings the compiler still narrows.
Example: `type Status = "pending" | "active" | "closed";`

**Branded types for ids** — why: two id types built on the same underlying string are
assignable to each other without a brand, letting the wrong id slip through unnoticed.
Example: `type UserId = string & { readonly __brand: "UserId" };`

**Parse at every external boundary** — why: data crossing a boundary (API response,
env var, file) is untyped until proven; parse it with Zod (or an equivalent) instead
of asserting its shape.
Example: `const user = UserSchema.parse(await res.json());`

## Mistake → problem → fix

| Mistake | Problem | Fix |
|---|---|---|
| any-leak | `any` on a boundary type propagates untyped values through the whole call chain | Type the boundary as `unknown` and narrow before use |
| assertion-cast | `as SomeType` bypasses the checker and hides real mismatches | Use `satisfies` so the checker still validates the shape |
| enum | `enum` adds runtime code and doesn't narrow cleanly against plain strings | Use a literal union type instead |
| naked-id | A plain `string` id can be passed where a different id type was expected | Wrap it in a branded type |
| unparsed-json | `JSON.parse()` / `res.json()` returns `any`, trusted without validation | Parse with a schema (Zod or equivalent) at the boundary |
