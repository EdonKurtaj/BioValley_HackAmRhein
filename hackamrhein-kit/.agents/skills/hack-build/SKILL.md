---
name: hack-build
description: Carry out one task from docs/plan.md in small verified steps. The assistant does the technical heavy lifting (backend, data, wiring, git) while the person steers the idea and checks results; explanations and decisions follow their profile. Use when someone says "build", "do T3", "let's code", "implement", "continue", or picks up a task from the plan.
---

# hack-build: do one task well

> Recommended setting: Luna High for planned tasks; Sol Medium for the T1 foundation, tricky logic or changes across many files; Luna Light for mechanical tasks. Suggest it once at the start if `model_hints: on` (`$hack-models`).

One task per chat. Something small that isn't in the plan: just do it and note it in the task's handoff file (tasks never edit `docs/plan.md`). Something big: suggest `$hack-brainstorm` or `$hack-plan` first.

You do the heavy lifting. For L0 to L2 you own the technical side completely; the person owns the idea, the domain rules and checking what they see on screen. Keep the process out of their way: checks, commits and docs happen quietly as part of your work.

## Start

1. Check the task's `Needs`: every listed task must be merged into `main`. If one isn't, say which, and offer a free task instead (`$hack-plan`, "what can I pick") or, if the person wants to go ahead anyway, build against the interface file with sample data and say that wiring comes later.
2. Read the task, the files it names, `docs/decisions.md`, and the handoff file if one exists (continue from its "Next"). Search for code you can reuse. Skim `../hack-review/references/standards.md` once per session.
3. Get on a fresh branch from `main`: `feat/t3-csv-upload` style, never a person's name.
4. One or two lines on what you'll do, in the person's style. In `teach` mode, ask what they think the first step is.

## First task of a project

When the repo has no code yet, T1 builds the foundation in one go: the walking skeleton (the app starts and shows the demo flow with sample data), the folder layout, a small interface file (`$hack-interface`), a package manager setup, one theme file with neutral defaults that all styling reads from (so the look can be decided or changed later in one place, `$hack-design`), and README run instructions that you've actually run. The stack decides the tool. If the team goes with Python, propose pixi (preferred, not required; one line why: everyone gets exactly the same setup). If they agree: `pixi init .`, `pixi add python <packages>`, `pixi add ruff pytest`, and tasks `start`, `test`, `fmt`, `lint` (`pixi task add start "streamlit run app.py"` and so on); if pixi isn't installed, ask once whether you may install it with the official one-line installer from pixi.sh. If they decline: a `.venv` with a pinned `requirements.txt`. For JavaScript: npm with scripts. Other stacks: their standard package manager. Log the stack, layout and package manager as lines in `docs/decisions.md`. Aim to have something on screen within the first hour.

## The loop

For each small step (one function, one screen element, one data transform):

1. **Decide.** Choices in areas the person owns (`choose` or `lead` in the profile): ask with A/B/C and one line of consequence each, in their world. Otherwise decide and mention it in one line. Team-relevant choices: one line in `docs/decisions.md`.
2. **Change.** The smallest clean change toward "done when": right layer (UI, logic, `config/`), shared models from the interface file, domain names, edit in place. If the step needs a new shared field or function, add it to the interface file with a decision line; if it would break someone else's code, follow `$hack-interface` first.
3. **Check.** Run it. For rules and calculations, test with real examples from the team ("give me 3 real cases and the right answer"). Say what you checked and what you saw, never "should work".
4. **Tell.** By profile: `do` one line; `do-explain` 1 to 3 lines, by effect for T0/T1; `teach` a hint, let them try, then look at it together; `pair` propose who does the next step. If they have learning goals, at most one short "here's what just happened" per task.
5. **Save.** New packages only through the project's package manager, recorded in its manifest. Run the formatter and the tests (with pixi: `pixi run fmt`, `pixi run test`), update any doc that mentions what you changed, update the handoff file (State, Done, Next in a few lines), commit. The hooks run the privacy check automatically; if it blocks, fix it (`$hack-guard`). For L0/L1 call it "saved a checkpoint" until they use the word commit themselves.

## Done

1. Check "done when" literally and show the person the result.
2. Handoff file: status `done`, plus anything the next person should know.
3. Update the branch from `main`, push, open a pull request, and offer to merge it (`$hack-pr`, always asking first). Code review happens there, not here.
4. Note in the local profile what the person now knows or did themselves (never in repo files).
5. Suggest a fresh chat for the next task.

## Running low or stuck

- Usage warning, long chat, or they have to stop: save the handoff in full first (`$hack-handoff`), then continue if there's room.
- Two failed attempts at the same problem: `$hack-unstuck`, not a third variation.
