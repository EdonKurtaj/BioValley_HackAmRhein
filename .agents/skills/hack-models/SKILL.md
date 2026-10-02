---
name: hack-models
description: Pick the cheapest Codex model (GPT-6 Luna, GPT-6.1 Sol, GPT-6 Astra) and thinking effort that does the job, and escalate only when needed, to save usage. Use when someone asks which model or effort to use, hits usage limits, says "too slow", "too expensive", "out of credits", before a big task, or at a task boundary when the profile has model_hints on.
---

# hack-models: right model, right effort, fewer tokens

Every participant has a ChatGPT Business seat for one month. Usage limits are per seat, in 5-hour windows, with possible weekly limits on top; local and cloud chats share them. Big tasks eat far more than small ones.

You can't switch your own model. You recommend, the person switches in the model and effort control under the message box (open **Advanced** to pick a specific model and effort; CLI: `/model`). One line, in their language. Details, IDs and sources: `references/models.md`.

## The three models the team uses

| Model | Pick it for | Cost per token vs Luna | Messages per 5 h (Business, rough) |
|---|---|---|---|
| **Luna** (`gpt-6-luna`) | Scoped, clear tasks: focused coding with a clear "done when", edits, extraction, explaining, git, summaries | 1x | 350 to 3,000 |
| **Sol** (`gpt-6.1-sol`) | Judgement: design, the foundation, work across several files, logic that's easy to get wrong, bugs Luna couldn't fix | about 20x | 15 to 160 |
| **Astra** (`gpt-6-astra`) | Last resort: one hard problem that Sol at Extra High couldn't crack | about 100x | 5 to 45 |

The key fact: Luna is so much cheaper that a Luna run at High or Extra High still costs a fraction of Sol. So **Luna with more thinking comes before Sol**, and Sol comes before Astra.

Don't pick: GPT-6 Sol (GPT-6.1 Sol is better at the same price), the GPT-5.6 models and GPT-5.5 (older, being retired), Max, Ultra, and Fast mode (Fast costs 2.5 times the usage; see below).

Efforts: **Light** (Low in the CLI), **Medium**, **High**, **Extra High**. More effort means more thinking, slower, more usage.

## Default setting per skill

| Skill / task | Setting | Why |
|---|---|---|
| `$hack-start` onboarding | Luna Medium | Conversation with a script |
| `$hack-brainstorm` | **Sol Medium** | Judgement and trade-offs, done once, shapes everything |
| `$hack-plan` | Sol Light | Splitting the work well matters for the whole team; short run |
| `$hack-build`, T1 foundation | **Sol Medium** | Structure, stack and interface file everyone builds on |
| `$hack-build`, planned task with a clear "done when" | **Luna High** | The default for most of the weekend |
| `$hack-build`, mechanical task (rename, move, reformat, text, CSV cleanup) | Luna Light | Clear result, no judgement |
| `$hack-build`, tricky logic or changes across many files | Sol Medium | Easy to get subtly wrong |
| `$hack-explain` | Luna Medium | Explaining is cheap |
| `$hack-design`, directions and style guide | Sol Light | Taste and judgement, short |
| `$hack-design`, theme file and style sample | Luna High | Clear, scoped work |
| `$hack-explain`, turning knowledge into rules | Luna High (Sol Light if the rules are subtle) | Precision matters |
| `$hack-interface`, additive change | Luna High | Small, follows the existing pattern |
| `$hack-interface`, breaking change | Sol Medium | Affects everyone's code |
| `$hack-review` | Luna Extra High (Sol Medium for a big or messy branch) | Checking against clear standards |
| `$hack-pr` | Luna High (Sol Medium for a hard conflict) | Careful, mostly routine |
| `$hack-unstuck` | Luna Extra High, then Sol Medium | See escalation below |
| `$hack-ship` | Luna High | Checklist work |
| `$hack-demo` pitch and slides | Sol Light | Seen by the jury, short text |
| `$hack-github`, `$hack-guard`, `$hack-team`, `$hack-handoff`, profile updates | Luna Light | Routine |

## Escalation: change one thing at a time

When a result isn't good enough, ask: did it lack **thinking** or **ability**?

- Incomplete, sloppy, missed a step, didn't find the relevant file: raise the **effort** on the same model.
- Wrong approach, misunderstood the problem, going in circles: go **up a model**, back at Medium.

The ladder: Luna Light, Luna Medium, Luna High, Luna Extra High, Sol Medium, Sol High, Sol Extra High, Astra Medium.

Step back down as soon as the hard part is solved: the next ordinary task goes back to its default. Astra is for one problem at a time, in a fresh chat with a tight summary, never as a working default.

## Splitting usage across the team

- Usage is per person. Whoever has the most left takes the Sol work (brainstorm, foundation, hard bugs).
- Plan the Sol moments: brainstorm and T1 on Friday, one or two hard problems per day. Everything else on Luna.
- Astra: at most one session per team per day, agreed at a sync, for the problem that blocks the demo.
- Sunday morning: keep some Sol in reserve for a last-minute bug.

## Fast mode

Fast mode answers quicker but costs 2.5 times the usage on the seat. Leave it off. The only good moment: Sunday, shortly before the demo, for a small fix on Luna when minutes matter more than usage.

## When to give a hint

Only at task boundaries, never mid-task, and only if `model_hints: on` (default on for L0 to L2, off for L3 and L4). One line: "This is a clear, scoped task: Luna High is enough and saves your usage." For T0 and T1, say "the lighter setting under the message box" if model names confuse them.

## Token-saving habits (teach once, in the person's style)

1. One task, one chat. Long chats resend everything and get slower and worse.
2. Point, don't search: name the file (`@app.py`).
3. Small tasks, as `$hack-plan` produces them. Small tasks are what make Luna enough.
4. Fresh chat plus handoff file instead of long histories (`$hack-handoff`).
5. Paste the last 20 to 30 lines of an error, not the whole log.
6. Two failed attempts: change approach or climb one step on the ladder, don't retry the same thing.
7. Ask for less output when that's enough: "just the changed function".

## When usage runs out

Before anything else, make sure the handoff is saved (`$hack-handoff`). Then say so plainly. The allowance is shared across all models: once it's used up, no model works until it resets (the 5-hour window; the usage view shows when). A turn that's already running may finish. Options: A a teammate with usage left takes the next task, B do the non-AI work now (pitch, test cases, rules, slides) until the reset.

**Running low, not out yet:** that's when Luna helps. It uses about a twentieth of Sol per token, so switching to Luna and keeping tasks small stretches what's left a long way. Suggest it as soon as someone mentions a usage warning.
