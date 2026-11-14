# Playbook: prototype

For one design question that throwaway code answers faster than discussion.

1. Write the question down in one sentence before any code. No question, no prototype:
   use `feature` instead.
2. Put the logic the question is about in a pure core (no database, network or
   framework) and run it from a shell named as throwaway (`main.throwaway.ts`).
3. Compare variants behind one switch in the same build, so all run under the same
   conditions. A new question gets a new prototype, not a patched one.

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST does not apply inside a prototype, and
only while all three hold: the code never merges, it is never adapted into production,
and it is deleted at the end. If any stops holding, delete the code and restart from a
failing test.

Exit, in order:

1. Record `DECISION <question> → <choice>` in the plan or the report, noting the
   prototype was deleted.
2. Turn each proven behavior into one test, delete the prototype, and build the real
   thing with the `feature` playbook from those tests.

Done when the decision line is written and the prototype is gone.
