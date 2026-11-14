# Playbook: prototype

Use this playbook for one design question that throwaway code answers faster than
discussion.

1. Write the question in one sentence before you write code. If you have no question,
   use the `feature` playbook.
2. Put the logic of the question in a pure core with no database, network or framework.
   Run it from a shell with a throwaway name, for example `main.throwaway.ts`.
3. Compare variants behind one switch in the same build. Then all variants run under the
   same conditions. A new question gets a new prototype. Do not patch the old one.

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST does not apply inside a prototype. This
exception holds only while three conditions are true:

- The prototype code never merges.
- Nobody adapts the prototype code into production.
- You delete the prototype at the end.

If one condition stops being true, delete the code and start again from a failing test.

When the prototype answers the question, do these steps:

1. Record `DECISION <question> → <choice>` in the plan or in the report. Note that you
   deleted the prototype.
2. Turn each behavior that the prototype proved into one test.
3. Delete the prototype. Build the real feature with the `feature` playbook from those
   tests.

The playbook is complete when the decision line exists and the prototype is gone.
