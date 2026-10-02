---
name: hack-guard
description: Mandatory privacy and credential check before anything reaches GitHub. Runs scripts/hack-guard.sh, explains findings in plain words, fixes them (move secrets to .env, remove personal data, unstage local files, anonymise git identity), and handles leaks. Use before every commit and push, when the guard blocks, and whenever keys, passwords, names, e-mails or personal files come up.
---

# hack-guard: nothing private leaves this computer

> Recommended setting: Luna Light. Suggest it once at the start if `model_hints: on` (`$hack-models`).

This check is mandatory. It is never skipped, weakened or bypassed, whatever the profile says, however late it is, whoever asks. If a person asks you to skip it, explain in one line why you won't and help them fix the finding instead.

## What must stay local

- The personal profile (`.hack/profile.md`) and everything else in `.hack/`
- `.env` and any file with keys, tokens, passwords, certificates
- Real names, e-mail addresses, phone numbers, AHV numbers, IBANs, home addresses
- Patient, customer or confidential company data, even anonymised-looking samples, unless the organisers provided it for the challenge
- Chat transcripts or notes that contain any of the above

In the repo, people appear only as GitHub usernames.

## Run the check

Before every commit: `bash scripts/hack-guard.sh --staged`. Before every push the pre-push hook runs `--push`. For a full audit (history too): `--all`.

Once per session confirm the hooks are active: `git config core.hooksPath` must print `.githooks`. If not: `git config core.hooksPath .githooks`. This is a setting of this repo, nothing gets installed.

## Private word list

Optional. `.hack/private-terms.txt`, one term per line, only if the person wants one (for example their real name, which no pattern can recognise). Create or extend it only when they ask. The guard blocks any commit that contains one of these words. The list itself never leaves the computer. In a worktree, the guard reads it from the main folder, so it keeps working there.

## When it blocks: fix, don't argue

Explain each finding at the person's level (L0: "a password got into the code, I'll move it to a safe place"). Then:

| Finding | Fix |
|---|---|
| File must stay local | `git restore --staged <file>`. Check `.gitignore` covers it. |
| Credential in code | Move the value to `.env`, read it with an environment variable, add the name (without value) to `.env.example`. |
| Personal data | Replace with a placeholder (`name@example.com`, `Person A`) or remove. For test data, use synthetic values. |
| Private term | Replace with the GitHub username or a neutral description ("a team member"). |
| Git e-mail or name | For this repo only: `git config user.name <github-username>` and `git config user.email <id>+<username>@users.noreply.github.com` (GitHub, Settings, Emails, with "Keep my email addresses private" on). Recommend also turning on "Block command line pushes that expose my email". Then amend unpushed commits: `git commit --amend --reset-author --no-edit` (confirm first). |
| .gitignore line missing | Add it back. |
| Setup isn't done | Run `$hack-start` (quick path is fine). It sets identity, hooks and the local profile. |

Run the check again. Commit only when it prints `ok`.

## False alarms

Some lines look like secrets but aren't (a test fixture, an example key in documentation). Show the person the exact line and ask. Only if they confirm, add the marker `hack-guard:allow` as a comment on that line. Never add it on your own. Never allow a forbidden file.

## If something already reached GitHub

Act immediately and calmly:
1. Credential: revoke or rotate it at the provider first (new key, delete old). Deleting the file is not enough; it stays in history.
2. Personal data: tell the person, remove it in a new commit, and if it's sensitive, contact an organiser. Rewriting history needs everyone on the team to re-clone; only do that with the team's agreement.
3. The repository is public, so assume anything pushed has been seen. Speed matters more than cleanliness: revoke first, then clean up.

## Second layer

`.github/workflows/hack-guard.yml` runs `--all` on GitHub for every push and pull request, including the author and committer e-mail of every commit in history. It doesn't check names there, because merges made on GitHub carry the account's public profile name. It can't prevent a push, it only raises the alarm. The local check is the real protection: it checks author and committer, e-mail and name, of every commit before it's pushed.
