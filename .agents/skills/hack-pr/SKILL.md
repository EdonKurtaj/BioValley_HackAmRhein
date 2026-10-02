---
name: hack-pr
description: Go over open pull requests to keep merge conflicts small: bring each branch up to date with main, resolve conflicts, run checks and review, then ask before merging and merge only after an explicit yes. Use when someone says "PR", "pull request", "merge", "go over the PRs", "conflicts", at team syncs, after a task is done, and before the Sunday demo.
---

# hack-pr: fewer conflicts, no surprise merges

> Recommended setting: Luna High (Sol Medium for a hard conflict). Suggest it once at the start if `model_hints: on` (`$hack-models`).

You may prepare, update, fix and merge pull requests. **You never merge without asking first.** Every merge gets its own explicit yes from the person in this chat, whatever their ownership or help settings. "Merge everything" counts as a yes only for the PRs you listed right before it.

## Why this exists

Conflicts grow with time and branch size. The cure is to merge small branches often and to keep every open branch close to `main`. This skill does that routine work so nobody has to be good at git to benefit.

## 1. See what's open

With the GitHub CLI (if installed and logged in): `gh pr list`. Without it: `git fetch --prune` and list remote branches not yet merged into `main` (`git branch -r --no-merged origin/main`). Also check the `handoff/` files to see which tasks are done.

Codex will ask to use the internet for fetch, pull and push. For L0 to L2, say so in one line beforehand.

Show the person a short list in plain words, oldest first: branch, task, what it changes (one line), and status (ready, needs update, has conflicts, checks failing).

## 2. Merge order

`iface/` pull requests (breaking interface changes) first, then smallest and oldest first. Foundation and shared-file changes (layout, config, README) before features. After each merge, the remaining branches are updated from the new `main` before the next one goes in.

## 3. For each PR: update, check, review

1. Check out the branch. Bring it up to date: `git merge origin/main` into the branch. Never rebase or force-push shared branches.
2. **Conflicts:** resolve them on the branch, not on `main`.
   - Keep both sides' intent where possible. Read the handoff files and `docs/decisions.md` to understand what each side wanted.
   - A lock file conflicting (`pixi.lock`, `package-lock.json`): never hand-edit. Resolve the manifest, then run `pixi install` or `npm install` to regenerate it.
   - Docs conflicting with docs: merge the facts and apply the one-home rule from the standards.
   - If the two sides really want different things, don't guess. Show the person both versions in plain words (for L0 to L2 by effect, not as conflict markers) and ask, or ask the owner from `TEAM.md`.
   - Run the app or the tests after resolving.
3. Run the checks: formatter, linter, tests including contract tests, `bash scripts/doc-check.sh`, and the privacy check (the hooks run it on commit and push).
4. Run `$hack-review` on the diff against `main`. "Must fix" findings get fixed on the branch first (small ones by you, larger ones: ask the branch owner or note in the handoff).
5. Commit the update and fixes, push the branch.

## 4. Ask, then merge

Ask for each PR, in the person's language and level, with lettered options:

> PR "feat/t3-csv-upload" (CSV upload shows the data as a table): up to date with main, tests and checks pass, review clean. Merge it now?
> A. Yes, merge  B. Not yet  C. Show me the changes first

- Only on an explicit yes: merge. With the GitHub CLI: `gh pr merge <number> --merge --delete-branch`. Without: `git switch main && git pull && git merge --no-ff <branch> && git push`; GitHub marks the pull request as merged. Then delete the branch if the person agrees.
- On "not yet": leave it, note why in the task's handoff file.
- Never merge a PR with failing tests, a blocked privacy check, or unresolved "must fix" findings, even if asked. Explain in one line and offer to fix it first.

## 5. After each merge

1. `git switch main && git pull`.
2. Update the remaining open branches from `main` (step 3.1) so they don't drift away.
3. Tell the team in one line what's now on `main`. The task's `handoff/` file (status `done`) came in with the merge; no separate status update is needed.

## Team rules this relies on

- Small branches, one task each, merged within hours, not days.
- Anyone's assistant may prepare and update any PR; merging needs the yes of the person running the chat, and the team's merge policy in `TEAM.md` (e.g. "one teammate looked at it") still applies.
- Sunday: go over PRs often, so what the team wants to show is on `main` and working before their demo.
