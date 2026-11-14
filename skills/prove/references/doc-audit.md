# Document audit

A document is a set of claims about code. Examine each claim against source that you read
in this session. Do not examine a claim against memory, another document or old logs. Do
not change code. Change the document only after the user approves the change.

Select one mode. Write the mode and the target in the first line of your output.

| Mode | When | Result |
|---|---|---|
| `audit` | An existing document can be out of date | A claim table, then an approved rewrite |
| `explain` | A subsystem needs a new explanation | A diagram, a claim table with citations, and unknowns |

Claims are facts about code: names, callers, data flow, config, schemas, endpoints,
paths and owners. Reasons, history, opinions and "should" statements are not claims.
Keep them and label them. Evidence is source code that you read now, never the document
under audit. Cite it as `path:line`, one citation for each file of the claim. Two
similar names do not prove the same component.

## Audit

1. Give each claim a number before you examine any claim. This step is complete when each
   factual sentence has a number.
2. Examine each claim. Report the table `# | Claim | Verdict | Evidence`.
3. Use one of three verdicts:
   - CONFIRMED.
   - CONTRADICTED. State what the code does.
   - UNVERIFIABLE. State what you read and why the claim stays open.
4. Stop and get approval. Then rewrite only the contradicted sections. Keep the voice and
   the structure. Make the table again for those sections.

## Explain

1. Draw a text diagram of the components and the direction of the data.
2. Make a claim table. Each statement has `path:line` evidence.
3. Write UNKNOWNS, with one reason each: a running system, another repository, or a
   configuration that only production has.
4. Write candidate changes when the evidence shows a problem. State the risk. Do not
   make the change.

The explanation is complete when each statement has a citation or an entry in UNKNOWNS.
