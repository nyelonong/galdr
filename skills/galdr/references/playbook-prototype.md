# Playbook: prototype

For one design question that throwaway code answers faster than discussion.

1. Write the question down in one sentence before any code. No question, no prototype:
   use `feature` instead.
2. Split the build: a pure core holding the logic the question is about (no database,
   network or framework), and a throwaway shell to run it, named as throwaway
   (`main.throwaway.ts`).
3. For "is X or Y better", build every variant behind one switch in the same build
   (`?variant=a`, a `-variant` flag, a feature flag) so all run under the same
   conditions.
4. When the question itself changes, start a new prototype instead of patching the old
   one.

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST does not apply inside a prototype, and
only while all three hold: the code never merges, it is never adapted into production,
and it is deleted at the end. If any stops holding, delete the code and restart from a
failing test.

Exit, in order:

1. Record the answer: `DECISION <question> → <choice>`, in the plan file if one exists,
   otherwise in the report.
2. Turn each behavior the prototype proved into one test for the real implementation.
3. Delete the prototype, and say so in the decision line.
4. Build the real thing with the `feature` playbook, starting from those tests.

Done when the decision line is written and the prototype is gone.
