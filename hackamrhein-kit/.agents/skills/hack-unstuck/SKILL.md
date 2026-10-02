---
name: hack-unstuck
description: Structured way out when something fails, errors, loops, or nobody knows why it broke. Reproduce, read the error, one hypothesis at a time, stop after two failed attempts and change approach, escalate to a mentor with a ready-made summary. Use for errors, "doesn't work", "broken", "stuck", "it worked before", the same fix failing twice, or rising frustration.
---

# hack-unstuck: get unstuck without burning hours

> Recommended setting: Luna Extra High, then Sol Medium, Sol High, Sol Extra High; Astra Medium only as the last step. Suggest it once at the start if `model_hints: on` (`$hack-models`).

## First, the person

Stuck is stressful. For L0 to L2 start with one calm line: what broke, that it's fixable, what you'll do. Don't show a wall of errors.

## The protocol

1. **Reproduce.** Run the exact thing that fails. Note the exact error, the last 20 to 30 lines, not more.
2. **What changed?** `git status`, `git diff`, `git log -5`. "It worked before" usually means a recent change broke it. If so, compare against the last working commit.
3. **Read the error literally.** File, line, message. Explain it at the person's level (`$hack-explain`).
4. **One hypothesis at a time.** State it in one line, make one change, re-run. Write down what you tried.
5. **Two strikes rule.** If two attempts at the same idea fail, stop. Don't try a third variation. Instead pick one:
   - A. Step back: is there a simpler way to reach the demo goal that avoids this problem entirely?
   - B. Go back to the last working commit on a new branch and redo the step smaller.
   - C. Stronger reasoning: climb one step on the ladder for this one problem (Luna Extra High, then Sol Medium, Sol High, Sol Extra High, Astra Medium as the very last step; `$hack-models`), in a fresh chat with a tight summary.
   - D. Ask a human: a teammate or a HackAmRhein mentor.
   Offer these as lettered options. For ownership `decide` in the affected area, pick and say why.
6. **Fix and protect.** Once fixed, add a quick check or test so it doesn't come back, commit, and update the task's handoff file.

## Time boxes

- Saturday: max 45 minutes on one bug before option A or D.
- Sunday: max 20 minutes, then cut the feature or fake it, and add it to the limits slide.
- In the last hour before the demo: work around rather than fix. The fallback demo exists for this.

## Asking a mentor or teammate

Write this summary for the person to send or read out (English, short):

```
Goal: <what should happen>
What happens: <exact error, one line>
Where: <file / page / command>
Tried: 1) ... 2) ...
Since: <last change that might matter>
Question: <one specific question>
```

## Loops and weird agent behaviour

If you notice you're repeating yourself, rewriting the same file back and forth, or the chat is very long: say so, update the handoff file (`$hack-handoff`), and suggest continuing in a fresh chat from it.

## Common hackathon culprits (check early)

Wrong folder, command run outside the project environment (with pixi: `pixi run <task>`, not plain `python`; with a venv: not activated), package installed but not recorded in the manifest, `pixi install`, `pip install -r requirements.txt` or `npm install` not run after pulling, missing `.env` or wrong key name, port already in use, file path with spaces or Windows backslashes, CSV with a different separator or encoding (Swiss data often uses `;` and Latin-1 or UTF-8 with BOM), a teammate's merge changed a shared file.
