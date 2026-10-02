---
name: hack-review
description: Review code and docs for maintainability and documentation drift before merging: structure, naming in domain language, duplication, dead code, tests, and whether every doc still matches the code. Use before merging a pull request, at syncs, when someone asks "review", "clean up", "is this good", "refactor", or when code or docs feel messy or out of date.
---

# hack-review: keep it clean, keep it true

> Recommended setting: Luna Extra High (Sol Medium for a big or messy branch). Suggest it once at the start if `model_hints: on` (`$hack-models`).

The standards are in `references/standards.md`. Read them first. They apply to every profile; the profile only changes how you explain findings.

## When

- Before every merge to `main` (the reviewer's assistant runs it on the pull request branch).
- At each team sync, a quick pass over `main`.
- On request, or when `$hack-build` finishes a task.

## How

1. See what changed: `git diff main...HEAD --stat`, then read the diff. Don't review the whole repo unless asked.
2. Run the machines: formatter and linter (`ruff format --check`, `ruff check`, or the npm equivalents), the tests, and `bash scripts/doc-check.sh`.
3. Check against the standards, in this order (most damaging first):
   - Broken or untested domain logic, red contract tests
   - Interface drift: models redefined locally instead of imported, parts bypassing the interface file, a breaking interface change that didn't update all callers
   - Docs that now say something false (the same-commit rule), facts copied into a second home
   - Logic in the UI layer, duplicated logic, domain values hardcoded instead of in `config/`
   - UI that ignores the style guide: colours, fonts or spacing written directly into components instead of taken from the theme file, status shown by colour only
   - Names that don't use the domain's words, unclear names
   - Dead code, commented-out code, debug prints, unused files
   - Style issues the formatter didn't fix
4. Report at most 7 findings, most important first, each with the file, the problem in one line, and the fix. Mark each as **must fix before merge** or **later**. Small fixes: offer to make them right away.
5. Explain at the person's level. For L0 and L1, say it by effect: "The rule for storage temperature is written in two places. If someone changes one, the app will contradict itself. I'll keep one." Don't lecture.

## Hackathon judgement

- Saturday: fix all "must fix" findings before merging.
- Sunday: only fix what risks the demo or makes docs false. Put the rest in `handoff/` as known debt.
- Never start a large refactor on Sunday.

## Doc drift sweep (at syncs and before shipping)

1. `bash scripts/doc-check.sh`: fix every missing path.
2. Run the README's install and run commands as written, in a fresh terminal. If they don't work exactly as written, fix the README.
3. Compare `docs/design.md` "What we build" and the demo flow with what the app actually does now. Update the design, not the app, if the team deliberately changed scope.
4. `docs/glossary.md`: every domain term used in code names is there, nothing listed that's no longer used.
