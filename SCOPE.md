# Scope

galdr stays small on purpose. A change is accepted when all of these conditions are
true:

1. **It fixes an observed failure.** Link or paste the session where an agent with
   galdr did the wrong thing. A rule that nobody saw broken is a guess.
2. **It goes into an existing skill.** Add no new skill that only combines existing
   skills. Add no skill for the workflow of one project.
3. **It fits the budget.** All six skills and their references stay at or under 7,400
   words. The descriptions that load in each session stay under 400 tokens.
4. **It follows the voice.** Skill text passes an ASD-STE100 linter with zero hard
   findings.
5. **It was tested.** Discipline rules (`prove`, `debug`) pass a pressure test with
   and without the skill. Other changes pass a retrieval spot-check.

Ideas that we considered and declined are in [`.out-of-scope/`](.out-of-scope/), one
row each, with the reason. Read that list before you propose a change.
