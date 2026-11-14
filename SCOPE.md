# Scope

galdr stays small on purpose. A change is accepted when all of these hold:

1. **It fixes an observed failure.** Link or paste the session where an agent, with
   galdr loaded, did the wrong thing. A rule nobody has seen broken is a guess.
2. **It lives in an existing skill.** No new skill that composes existing ones, and no
   skill for one project's workflow.
3. **It fits the budget.** All seven skills and their references stay at or under
   5,500 words, and the descriptions that load every session stay under 400 tokens.
4. **It was tested.** Discipline rules (`tdd`, `verify`, `debug`) pass a pressure test
   with and without the skill; other changes pass a retrieval spot-check.

Ideas that were considered and declined live in [`.out-of-scope/`](.out-of-scope/),
one file each, with the reason. Check there before proposing something.
