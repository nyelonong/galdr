# Document audit

A document is a set of claims about code. Check each claim against source read in this
session, never against memory, another document, or old logs. Read-only until the user
approves a document write; never change code.

Pick one mode and state it, with the target, in the first line of output:

| Mode | When | Deliverable |
|---|---|---|
| `audit` | An existing document may have drifted | Claim table, then an approved rewrite |
| `explain` | A subsystem needs a new explanation | Diagram, cited claim table, unknowns |

Claims are component names, callers, data flow, queues, config keys, schemas, retries,
timeouts, endpoints, flags, paths and owners. Rationale, history, opinions and "should"
statements are not claims; keep them and label them as such. Evidence is source cited
as `path:line`; a claim spanning files cites each file. Similar names do not prove the
same component.

## Audit

1. Number every claim before checking any; done when each factual sentence maps to one.
2. Check each and report `# | Claim | Verdict | Evidence`, with verdict exactly
   CONFIRMED, CONTRADICTED (state what the code does) or UNVERIFIABLE (state what was
   inspected and why it cannot be decided).
3. Stop for approval. Then rewrite only the contradicted sections, keeping voice and
   structure, and re-run the table for them.

## Explain

1. A text diagram of components and data direction.
2. A claim table where every statement has `path:line` evidence.
3. UNKNOWNS, one reason each (running system, another repo, production-only config).
4. Candidate changes when evidence shows a problem, with risk, not implemented.

Done when every statement has a citation or is listed under UNKNOWNS.
