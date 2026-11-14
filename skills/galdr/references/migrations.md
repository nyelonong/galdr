# Migrations

Read before writing any schema change or migration.

1. Find the migration directory, the runner, how it orders migrations, and how it
   records which ones ran.
2. Confirm the version or sequence number you plan to use is not taken.
3. Trace each changed table or column through every writer, reader, query and
   validation that touches it.
4. Edit an existing migration only while it has never run outside your machine. Once it
   has run in any shared, test, staging or production database, add a new migration
   instead; never rewrite applied history.
5. If you cannot tell whether a migration has run somewhere, ask before editing it.
6. Keep a change that live code depends on backward compatible across a deploy: add the
   new column or table first, backfill, switch the code, and drop the old one in a later
   migration.
7. Keep destructive steps (drop, narrowing a type, deleting rows) in their own migration,
   and say in the plan how the data could be recovered.
8. Test the migration against an isolated real database, applying it from the previous
   version, not against mocks.

Done when the plan names the migration's version, the readers and writers it affects,
and the database it was tested against.
