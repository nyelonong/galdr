# Schema and migrations

Read this file before you design a schema or write a migration.

## Design

- Design tables only for approved current features.
- Keep in the database only the constraints that it must protect alone: identity,
  ownership, authorization, references, uniqueness and enforced invariants.
- Keep states, transitions, formats and version rules in application code. Move one to
  the database only for an approved correctness requirement.
- Prefer soft deletion for business records. Keep their foreign keys and ownership
  constraints. Add a hard-delete cascade only for an approved retention, privacy or
  correctness need. Without that need, a foreign key uses `RESTRICT` or `NO ACTION` on
  delete.
- If a foreign key cannot exist, for example across two services or two databases, name
  the application check that replaces it and its test.
- Add a check, constraint or index only for a current correctness requirement, a
  current query, a uniqueness requirement or a measured need. Do not add two guarantees
  that do the same thing.

## History

1. Find the migration directory, the runner, its order of migrations, and its record of
   the migrations that ran.
2. Make sure that nothing uses the version number that you plan to use.
3. Trace each changed table and column through its writers, readers, queries and
   validation. Search for copies of the same SQL. Change each copy that must stay the
   same.
4. Edit a migration only while it never ran outside your machine. If it ran elsewhere,
   add a new migration. If you do not know, ask. Never rewrite applied history.
5. For a change that live code depends on, keep compatibility across one deploy. Add the
   new column or table, fill it, switch the code, and drop the old one later.
6. Put each destructive step (drop, narrower type, deleted rows) in its own migration.
   Write in the plan how to recover the data.

## Proof

1. Run the migration linter or runner of the repository, if one exists.
2. Apply the migration from the previous version on an isolated real database. Do not
   use mocks.
3. Read the resulting schema. Make sure that the necessary constraints and indexes exist.
4. Test rollback only where the repository supports it and depends on it.
5. Never change tests or checks to make a schema check pass.

The work is complete when the plan names the version, the affected readers and writers,
and the database of the test.
