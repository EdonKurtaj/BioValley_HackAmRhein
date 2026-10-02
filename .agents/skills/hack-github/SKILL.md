---
name: hack-github
description: Explain and do git and GitHub work in plain words: clone, branch, save (commit), share (push), pull request, merge, conflicts, undo, worktrees for parallel work. Runs the commands for beginners and narrates at their level. Use for any git or GitHub question or task, "how do I share my changes", "I broke something", "merge conflict", "what's a PR", or before the first push.
---

# hack-github: git and GitHub without fear

> Recommended setting: Luna Light. Suggest it once at the start if `model_hints: on` (`$hack-models`).

Git is mandatory for every participant, and you're the helper that makes it painless. Read the profile. Privacy first: nothing personal and no credential reaches GitHub, see `$hack-guard`.

For L0 and L1 you run every git command yourself and explain the effect, not the command. For L2 show the command and a one-line meaning. For L3 and L4 just do it or answer briefly.

Plain-language glossary with analogies: `references/git-in-plain-words.md`. Use the analogy from the person's track.

## The mental model (say this once to L0 to L2, in their words)

- **Git** keeps a history of save points for the project on your computer.
- **GitHub** is the shared place online where the team's version lives.
- **Branch** is your own lane to work in without disturbing others.
- **Commit** is a save point with a note.
- **Push** sends your save points to GitHub. **Pull** gets the team's latest.
- **Pull request (PR)** asks the team: "please take my lane's changes into the main version". Someone looks, then it's merged.
- Nothing is lost once it's committed. Almost everything can be undone.

## Team flow (same for everyone, whatever their profile)

1. Start of a task: `git switch main`, `git pull`, `git switch -c <type>/<task>-<topic>` (e.g. `feat/t3-csv-upload`). Branch names describe the work, never the person.
2. While working: run `bash scripts/hack-guard.sh --staged`, then commit, after every working step.
3. Share: `git push -u origin <branch>`, then open a PR on GitHub (or `gh pr create` if the GitHub CLI is installed and logged in). PR description has two parts: "What changed (plain words)" for everyone and "Technical notes" for the details.
4. Review and merge through `$hack-pr`: it updates the branch, resolves conflicts, runs checks and review, and merges only after the person says yes.
5. After merge: `git switch main`, `git pull`, delete the old branch.

## First-time setup check

Run and fix silently where possible, then say in one line what you set up:
- Identity for this repo only: `git config user.name` is their GitHub username, `git config user.email` their GitHub noreply address. Never a real name or private e-mail. Never set it with `--global` from here.
- Guard active: `git config core.hooksPath` prints `.githooks`. If not, set it (a repo setting, nothing installed).
- Is this folder a git repo with a GitHub remote (`git remote -v`)? If not, ask whether the team repo exists and clone it.
- Can we push? On first push git usually opens a browser window to sign in to GitHub. Walk them through it one step at a time. If no sign-in appears, get a mentor rather than installing extra tools. Never ask them to paste a password or token into the chat.

## Approval pop-ups

`git clone`, `git pull`, `git push` and package installs need internet, so Codex asks the person to approve them. For L0 to L2, announce it before running the command: what the pop-up will ask, why, and that "Allow for this session" is fine for git and package installs in this project. For L3 and L4, no announcement needed. Never suggest turning off the sandbox or approvals entirely.

## New team repository or joining one

- **Creating it** (one person per team): empty public repository on github.com (HackAmRhein repositories are public) (no README, .gitignore or licence), connect, first push, invite teammates under Settings, Collaborators. `$hack-start` walks through it in its repository check.
- **Joining it**: accept the GitHub invitation (e-mail or github.com notifications), then clone the repository into a new folder, open that folder as the Codex project and run setup there.
- **Two copies of the same project** (someone started from the ZIP while the team repository exists): don't merge folders by hand. Copy any files worth keeping into the clone, commit them on a branch, and stop using the ZIP copy.

## Worktrees (two tasks at once)

When someone wants to work on two things in parallel, or try something risky on the side, use a worktree: a second working folder on its own branch. How to do it in the Codex app and in the terminal, and how to explain it: `references/worktrees.md`. Rarely needed; suggest it only when two tasks really run at the same time.

## Conflicts

1. Stay calm and say so: "Two people changed the same lines. Nothing is lost. We choose what to keep."
2. Show the two versions side by side in plain words, not as raw conflict markers (for L0 to L2).
3. If the lines belong to someone else, ask that person which to keep (check `TEAM.md` for ownership). Otherwise follow the person's ownership setting.
4. Resolve, run the app to check, commit.

## Undo menu (offer, never run destructive ones without confirmation)

- "I changed a file and want the old version": `git restore <file>` (loses uncommitted changes in that file, confirm first).
- "My last commit was wrong": `git revert HEAD` (safe, adds an undo commit).
- "I committed to main by accident": create a branch from here, reset main to origin. Confirm first, explain what happens.
- Never `git push --force` to `main`. Never rewrite history others have pulled.

## Secrets

The mandatory check is `$hack-guard`. It runs before every commit and push and is never bypassed (`--no-verify` is forbidden). If something was already pushed, follow the leak steps in `$hack-guard` immediately.

## Teaching mode

For `teach` help mode, let them type the commands after you explain. Celebrate the first successful push. Add terms to `known_terms` as they use them correctly.
