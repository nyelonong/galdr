# Comment placement

The placement half of the **Comments** smell in `SKILL.md`. The bar for whether a
comment exists at all lives there; this file says where one goes once it clears the bar,
and which placements are worth a finding. A repo's own documented comment standard
overrides every row here.

| Level | Placement | Bar to clear |
|---|---|---|
| File | One line at the top | A file whose name does not say what it holds |
| Declaration (type, struct, class, interface, enum, service, exported function) | The line above | Rises the more the name already says |
| Member (field, property, enum value, column, config key) | Beside it, same line | Only when the name does not carry it |
| Inside a function body | None | A named variable or an extracted function carries it instead |

## What to flag

- **A member commented on the line above.** Above pushes members apart and makes the
  type harder to read as one shape. Move it beside the member, same line.
- **A comment inside a function body.** The fix is a named variable or an extracted
  function, not a reworded comment.
- **A declaration comment that repeats its own name.** The better the name, the higher
  the bar the comment has to clear; a name that already carries it wants no comment.
- **Three lines or more.** One line is the norm, two only when the why needs it. Past
  that it is a decision, so it belongs in a doc in the repo, not above the code.

## What not to flag

Existing files that comment their members above stay as they are. Judge the added and
changed comment lines in the diff; a file-wide restyle is not a review finding, and
proposing one is creep.
