---
name: hack-plan
description: Turn docs/design.md into a short list of small, checkable tasks with owners, written to docs/plan.md. Each task fits in one chat and has a clear "done" check. Use after brainstorming, when someone asks "what do we do next", "split the work", "make a plan", or when a task feels too big to start.
---

# hack-plan: design to small tasks

> Recommended setting: Sol Light. Suggest it once at the start if `model_hints: on` (`$hack-models`).

Input: `docs/design.md`, `TEAM.md`, `docs/decisions.md`. Output: `docs/plan.md`. No code written here.

## Rules for a good task

- Fits in one chat and about 30 to 90 minutes. If not, split it. The one exception is T1, the foundation (see below): it stays one task because everything else builds on it, and it runs on Sol so it goes fast.
- Has an owner (GitHub username, never a real name). A buddy only if the owner asks for one or says they haven't used git before; agree it in chat.
- Has a "done when" line that anyone can check without reading code: "uploading sample.csv shows 12 rows in the table".
- Names the files it will touch, so two people don't edit the same file at once.
- Says what it needs first (`Needs: T1, T3` or `Needs: nothing`). Only real dependencies: it uses code, data or a decision another task produces.
- Is ordered so there is a working, demo-able thing as early as possible. First task: a walking skeleton (the app starts and shows something). Then add real pieces.
- Non-code tasks are real tasks: rules, real test cases, sample data, the look and style guide (`$hack-design`), pitch story, sources list. Schedule them early; the code tasks depend on them.

## Steps

1. Read the design. If anything is unclear enough to block a task, ask one question at a time.
2. Draft the tasks using `assets/plan-template.md`: milestones as headings, tasks under them. Each milestone heading says in one line what works once it's done. Inside each milestone, sort the tasks into chunks (see "Parallel or in order" below).
   - M1 Walking skeleton (Friday night or Saturday morning). T1 is always the foundation in one task: the app runs end to end with sample data, folder layout, a small interface file, test command, README run instructions (see `$hack-build`). Merge it early so everyone builds on it.
   - M2 Core demo flow works with sample data (Saturday evening)
   - M3 Polish, fallback, slides (Sunday, up to the demo)
3. Show the plan to the person adapted to their profile:
   - Skill levels and profile details never go into the plan. Buddy pairing is proposed in chat, not justified in the file.
   - Translation level T0/T1 (from the profile, not the task numbers): show milestones and their own tasks in plain words. Keep the file detail for the file.
   - `architecture: choose|lead`: point out where the task split implies a technical choice and let them confirm.
4. Assign owners with the team if people are present. Otherwise propose owners based on what each person works on in `TEAM.md` and mark them `(proposed)`.
5. Write `docs/plan.md`, commit on `docs/plan`, open a pull request and offer to merge it through `$hack-pr` (after asking) so everyone sees the same list.
6. Show the team which tasks are free right now, then tell each person how to start: "Open a fresh chat, type `$hack-build` and the task number."

## Parallel or in order

Teams pick tasks from the plan, so the plan shows at a glance what can happen at the same time. Each milestone is split into chunks, labelled `parallel` or `in order`, and chunks are listed in the order they can start.

- **Parallel chunk:** no task in it needs another task in the same chunk, and no two of them touch the same file. Anyone can pick any of them at once. If two tasks would share a file, split the file's work differently or move one to a later chunk.
- **In order chunk:** each task needs the one above it. Keep these short; a long chain means one person waits while others idle.
- Aim for as many parallel tasks as there are people, as early as possible. After T1 is merged, most of M2 should be parallel, because the interface file lets parts be built against each other before they're connected.
- Non-code tasks (sample data, domain rules, test cases, look, pitch story, sources) usually need nothing and go in an early parallel chunk. They're the natural first pick for anyone while T1 is being built.
- `Needs` on each task is the source of truth; the chunk label is the overview. They must agree. A task is free to start when every task under `Needs` is merged into `main` (its handoff says `done`).

When someone asks what to pick ("what can I do?", "what's free?"): read the plan and the `handoff/` files, then list the tasks whose `Needs` are met and that have no handoff file yet (nobody started them). Prefer the earliest chunk, and the person's own areas from `TEAM.md`.

## Task format

Under its chunk heading (the headings say the milestone and chunk, so the task doesn't repeat them):

```
#### T3 Upload a CSV and show it as a table
Owner: @octo-cat · Buddy: @pixel-dev
Needs: T1
Files: app.py, src/<project>/loading.py
Done when: dropping data/sample.csv on the page shows its rows in a table.
Notes: uses the Batch model from the interface file.
```

The plan has no status field. A task's status lives only in its `handoff/<task>.md` file (`in progress`, `blocked`, `done`), which travels with the task's own branch and pull request. No task ever edits `docs/plan.md`, so the plan never causes merge conflicts. A task without a handoff file hasn't started.

## Replanning

When the plan meets reality (it will), update `docs/plan.md` instead of improvising: on a `docs/replan` branch, merged through `$hack-pr` after asking. Cut from M3 first, then from M2. Never cut the fallback demo.
