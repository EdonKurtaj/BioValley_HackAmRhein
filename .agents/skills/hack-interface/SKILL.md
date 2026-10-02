---
name: hack-interface
description: Keep the code's structure with a small shared interface file: the data models that pass between the parts and what each part offers. Set up with the walking skeleton, extended as features need it, checked by contract tests. Use when setting up a project, when a feature needs new shared data or a new function, or when someone says "interface", "contract", "data model", "structure".
---

# hack-interface: a light skeleton for the code

> Recommended setting: Luna High for additive changes, Sol Medium for breaking changes. Suggest it once at the start if `model_hints: on` (`$hack-models`).

One small file says which data passes between the parts of the app and what each part offers. It keeps many assistants writing into one repo from inventing their own shapes. It's guidance for structure, not bureaucracy: keep it minimal and let it grow with the features.

## Where it lives

- Python: `src/<project>/interfaces.py`. Template: `assets/interfaces.py`.
- JavaScript/TypeScript: `src/interfaces.ts`. Template: `assets/interfaces.ts`.

Its docstrings are the documentation. `docs/design.md` links to it and never copies it.

What goes in: shared data models named in the domain's words, the input format (e.g. required CSV columns), and short contracts for the main parts (loader, rules, output). Nothing else: no implementation, no config values.

## Setting it up

Part of the foundation task, together with the walking skeleton (`$hack-plan` T1). Not a separate step:
1. Take the parts and data flow from `docs/design.md`.
2. Write the smallest interface file that makes the skeleton work end to end.
3. Show the data models to the team in plain words ("each batch has an ID, a temperature and a date; the rules give back a traffic light with a reason"). They check that names and meanings match the real world. That's the most valuable minute here.
4. Add the contract tests (`assets/test_contracts.py`, run by the test command, e.g. `pixi run test`; for TypeScript `npx tsc --noEmit` as an npm script) and one line in `docs/decisions.md`.

## Changing it

- **Additive changes** (a new optional field, a new model, a new function): do it in the feature branch that needs it. Add one line to `docs/decisions.md` in the same commit, update the contract tests if a new part appears. Mention it in one line to the person and in the task's handoff.
- **Breaking changes** (renaming or removing a field, changing what a function takes or returns): these affect teammates' work. Say so in one line, check with the owners of affected parts (`TEAM.md`), then make it a small `iface/<topic>` pull request that updates every implementation and caller (`git grep` the old names). Merge it first through `$hack-pr` (ask before merging), then continue.

The pre-commit hook only checks one thing: a commit that changes the interface file also changes `docs/decisions.md`.

## Building against it

Import the shared models instead of redefining them, implement the contracts, and let parts talk only through them. Register each new implementation in the contract tests. That's all.
