# Worktrees: a second desk


Picture for L0 to L2 (use their track's analogy from `../../hack-explain/references/analogies.md`): a worktree is a second desk with its own copy of the project, on its own branch. You can work at both desks at once. Nothing on one desk moves things on the other. When you're happy, you bring the result back through a normal branch and pull request.

## When to use one

- Two tasks at once on one laptop (e.g. you let the agent build T4 while you and the agent fix a bug in T3).
- Trying something risky or experimental.
- Reviewing or running a teammate's branch without stashing your own work.

When not to: if one task at a time is going fine, a normal branch is simpler. Don't open more than 2 or 3 at once at a hackathon; you'll lose track.

## Option A: the Codex app (recommended for L0 to L2)

1. New chat. Under the message box, choose **Worktree** instead of Local.
2. Pick the branch to start from, usually `main` (freshly pulled).
3. Give the task, e.g. "`$hack-build` T4".
4. When it works: use **Create branch here** and name it `<type>/<task>-<topic>` (e.g. `feat/t4-chart`), then commit and push, then open a PR (see `$hack-github`). Or use **Hand off** in the chat header to move the chat and changes to your normal local folder.
5. Archive the chat when done. The app cleans the worktree up (it keeps snapshots you can restore). Worktrees you turned into a permanent branch are not deleted automatically.

Worktrees start without your uncommitted changes and without files that git ignores, such as `.env` and `.hack/`. Read the profile from the main folder (first line of `git worktree list`). If the app needs secrets, copy `.env` in by hand; the guard blocks it from being committed. Hooks and the repo's identity settings apply in worktrees too; check `git config user.email` shows the noreply address before the first commit.

## Option B: terminal (L3 and L4, or when you run it for someone)

```
git switch main && git pull
git worktree add ../<repo>-<topic> -b feat/<task>-<topic>
cd ../<repo>-<topic>
# copy .env if needed, install dependencies, work, commit, push, PR
cd -
git worktree remove ../<repo>-<topic>   # after the PR is merged
git worktree prune
```

List them with `git worktree list`. A branch can only be checked out in one worktree at a time.

## Team rules

- Every worktree is on a branch that follows the naming rule `<type>/<task>-<topic>` before anything is pushed.
- Mark the task in `docs/plan.md` as `doing (@<github-username>, worktree)` so teammates know.
- Merge small and often. A worktree that lives all Saturday will conflict on Sunday.

## Explaining it

For T0 and T1, don't say "detached HEAD" or "checkout". Say: "I'm working on a separate copy so your version stays untouched. When it works, I'll bring it over."
