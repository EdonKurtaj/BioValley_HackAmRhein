---
name: hack-team
description: Set up and run the team layer so people with different profiles and skill settings work in one repo: TEAM.md with roles and file ownership, a shared decision log, handoff notes and quick syncs. Use at team formation, when adding a person, when someone asks "who does what", "what did we decide", "sync", "standup", "handoff", or when two people step on each other's work.
---

# hack-team: many profiles, one repo

> Recommended setting: Luna Light. Suggest it once at the start if `model_hints: on` (`$hack-models`).

Everyone's assistant adapts to its person. That only works if the shared files are predictable. This skill owns those files: `TEAM.md` and `docs/decisions.md`. Live task state lives in `handoff/` (`$hack-handoff`). Like everything else, these files change on a branch and reach `main` through a pull request, merged after asking. All of them in English, plain words, no personal jargon, and no personal data: people appear only as GitHub usernames (`$hack-guard`).

## Set up the team (once, Friday evening)

0. One shared repository per team. If there isn't one yet, one person creates it (`$hack-start` repository check, option B) and invites the others as collaborators; everyone else clones it and runs setup there. Nobody keeps working in a separate ZIP copy.
1. Check if `TEAM.md` exists. If not, copy `assets/team-template.md` to `TEAM.md`.
2. For each person: GitHub username, what they're working on (e.g. "rules", "upload", "data", "pitch") and which areas or files they own. Nothing else. No real names, backgrounds, skill levels or learning goals: those stay in each person's local profile. Coordinate pairing and strengths in conversation, not in the file.
3. Agree the working rules at the bottom of the template: merge policy (who has to look at a PR before it's merged), sync times.
4. Create `docs/decisions.md` from `assets/decisions-template.md` if missing.
5. Everyone who hasn't yet: `$hack-start` in their own chat.
6. Commit on `chore/team-setup`, open a pull request and offer to merge it straight away through `$hack-pr` (asking first, as always), so everyone builds on it.

Don't sort people into types. Ask what each person wants to work on and let the areas follow. Their assistant fills whatever is missing, including all of the coding if nobody on the team codes. Two areas always need a name: the demo flow end to end, and time (keeps an eye on the schedule for the team, if the team wants that).

## Decisions

Anything a teammate's agent needs to know goes into `docs/decisions.md`: stack, data format, folder layout, API shape, naming, deploy target, what we fake. Format:

```
- 2026-10-03 · Store results as CSV, not a database · @octo-cat, @pixel-dev · Affects: T5, T6, deploy · Why: fastest to demo, jury can open the file · Instead of: SQLite, more setup for no demo benefit
```

Always exactly one line per decision: git merges this file by keeping everyone's lines (`.gitattributes`), which only works cleanly for one-line entries. Before any agent makes a team-relevant choice, it reads this file. If a new choice contradicts an old one, ask the owner, then add a new line starting with "Replaces <date> <old decision>:". Never edit old lines.

## Syncs (10 minutes, every few hours)

Suggest syncs at natural points: Saturday late morning, after lunch, early evening, Sunday morning. The people talk; you do the bookkeeping:
- Each person: done, next, blocked. Whoever is free picks from the tasks whose `Needs` are met (`$hack-plan`, "what can I pick"). Unblock first: pair the blocked person with whoever can help, or let their assistant take the technical part.
- You then, quietly: go over open pull requests and merge finished ones after asking (`$hack-pr`). Task status needs no bookkeeping: it lives in each task's `handoff/` file and arrives on `main` with the task's pull request. Read those files for the overview.
- If scope changed: update `docs/plan.md` and `docs/design.md` together on a small `docs/replan` branch and merge it through `$hack-pr` (after asking).
- If behind: cut from M3 first. Never cut the fallback demo.

## Handoffs

Handled by `$hack-handoff`: each task has a rolling summary in `handoff/`, updated after every step and when someone runs low on usage or has to stop. The next person says "continue T3" and their assistant picks it up, instead of asking anyone to re-explain.

## Conflicts between people

If two people want different things: summarise both positions in plain words (use `$hack-explain` between-teammates mode), name the tradeoff, and suggest that the owner of that area decides within 5 minutes. Log it. Hackathons reward decisions over perfect decisions.

## New person joins or someone leaves

Joining: `$hack-start`, add them to `TEAM.md`, give them one self-contained task from the plan. Leaving: make sure their handoff files are current and pushed, reassign their `doing` tasks.
