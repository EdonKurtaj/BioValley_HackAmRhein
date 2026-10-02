---
name: hack-handoff
description: Keep a rolling handoff summary of the current task in handoff/, updated automatically after every working step and whenever usage or the chat is running out, so a new chat or a teammate can continue without re-explaining. Use when someone says "limit", "running out", "summarise", "handoff", "I have to stop", "continue T3", "pick up", or when a chat gets long.
---

# hack-handoff: never lose the thread

> Recommended setting: Luna Light. Suggest it once at the start if `model_hints: on` (`$hack-models`).

You can't see how much usage a person has left, and a chat can hit its limit mid-sentence. So the handoff is not written at the end. It is **kept up to date the whole time**: when the limit hits, the latest state is already saved.

## Where

One file per task: `handoff/<task>-<topic>.md`, e.g. `handoff/t3-csv-upload.md`. Work that isn't a plan task: `handoff/<type>-<topic>.md`, e.g. `handoff/fix-login-crash.md`. Use `assets/handoff-template.md`.

It lives on the task's branch and is committed together with the work, so a teammate gets it with `git fetch` and `git switch <branch>`. One file per task means no merge conflicts between people.

## When to update (automatic, don't ask)

1. **After every working step**, as part of saving: update "State", "Done" and "Next", then commit it together with the code. Keep it short, rewrite rather than append.
2. **Immediately, before anything else, when a limit is near:**
   - the person mentions a usage warning, a limit, credits, or "running out"
   - Codex shows a context or compaction notice, or earlier details of this chat start to get fuzzy for you
   - the chat is long: roughly 25 or more exchanges, or many large files read
   - the person says they have to stop, go, sleep, eat, or hand over
   - you're about to suggest a stronger model or a fresh chat
   Write the full handoff, run the privacy check, commit it (and push, if the branch is already on GitHub), then tell the person in one line: "Saved where we are in handoff/t3-csv-upload.md. A new chat can continue from there."
3. **At the end of a task**: final version with status `done` and anything the next person should know.

Never let a handoff update grow into long work. If usage is nearly gone, the handoff comes first and the code second.

## What goes in

Only what a stranger needs to continue: goal, where things stand, what's done, the exact next steps, files involved, decisions made, open questions, known problems. Plus a ready-to-paste resume prompt.

Never: personal details, real names, profile information (levels, preferences), secrets, or chat transcripts. People appear only as GitHub usernames. The privacy check (`$hack-guard`) runs on it like on any other file.

Write it in English in plain words, so every teammate's assistant can read it. Explain to the person in their own language and level.

## Resuming

When someone opens a new chat and says "continue", "pick up T3" or similar:
1. Read `handoff/` for that task. If you don't know which task, list the open handoffs (status not `done`) and ask which one, as lettered options.
2. If it's on a branch you're not on: `git fetch`, then switch to that branch (tell L0 to L2 in one line what's happening; Codex may ask to use the internet).
3. Summarise in 2 to 3 lines in the person's language and level, then start with the first item under "Next".
4. If the previous person is a teammate, don't ask them to re-explain. Only message them if "Open questions" blocks the next step.

## Team view

At syncs (`$hack-team`), list the files in `handoff/` with their status line: that's the live overview of who is on what. When a task's branch is merged, the handoff file comes along into `main` as a record; that's fine.
