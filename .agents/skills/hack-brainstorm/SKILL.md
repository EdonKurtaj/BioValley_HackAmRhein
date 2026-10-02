---
name: hack-brainstorm
description: Turn a challenge or rough idea into an agreed, demo-able design before any code is written. Asks one question at a time, explores 2-3 approaches, cuts scope to what fits by Sunday, and writes docs/design.md. Use whenever someone wants to build something new, add a big feature, says "idea", "what should we build", "brainstorm", or starts coding without a design.
---

# hack-brainstorm: from idea to design

> Recommended setting: Sol Medium. Suggest it once at the start if `model_hints: on` (`$hack-models`).

No code in this skill. The output is a short design doc the whole team agrees on. Read the person's profile first: ownership decides which questions you ask them and which you answer yourself.

## Principles

- One question per message. Lettered options where possible. Their answer shapes the next question.
- Start from the problem and the people who have it, not from technology.
- The team's knowledge of the problem must be load-bearing. At HackAmRhein the challenge cannot be solved by code alone. If the design would work just as well without the domain person, it's the wrong design.
- Demo first. Every design answers: "What will the jury see in 3 minutes on Sunday?"
- YAGNI hard. Cut anything that does not show up in the demo. Faking parts is fine and honest if the limits slide says so (hardcoded sample data, a manual step behind the scenes).
- Time is the main constraint. Assume about 10 focused build hours for the whole team between Friday night and Sunday afternoon.

## Team mode

If several people sit together: one person types, everyone answers. Ask questions to the whole team ("question for whoever knows the lab side"). Direct tech questions to whoever owns that area in `TEAM.md`.

## Quick mode (default on Friday evening, about 15 minutes)

Team formation happens over drinks, so start light:
1. Three questions, one at a time: who has the problem and when does it hurt, what do they do today, what should the jury see in 3 minutes.
2. Two approaches with one line each, recommend one.
3. Write a half-page `docs/design.md` (problem, demo flow, data, out of scope) and stop.
Offer the full version below for Saturday morning if the team wants to go deeper. Most teams won't need it.

## Full mode

 (4 to 8 questions)

Look at what exists first: the challenge brief, `README.md`, any data in the repo, `TEAM.md`, `docs/decisions.md`. Don't ask what you can read.

Then ask, one at a time, skipping what you already know:
1. Who has this problem? Describe one real person and one real moment when it hurts.
2. What do they do today instead? (the workaround is the baseline you must beat)
3. What does "better" look like for them? Faster, fewer errors, cheaper, safer, fairer?
4. What does the team know about this problem that an outsider would get wrong? Ask for one concrete pitfall.
5. What data or inputs exist? Is it provided, public, or would it need to be invented for the demo?
6. What must NOT happen? (patient safety, privacy, regulations, trust)
7. What's the smallest version that would make the problem owner say "I'd use that"?

## Phase 2: approaches (2 or 3)

Present 2 or 3 genuinely different approaches. For each: one-line idea, what the demo shows, rough effort (S/M/L), biggest risk. Lead with your recommendation and why.

Adapt to profile:
- Translation T0/T1: describe approaches by what the user experiences ("a web page where you drop your batch record and get a traffic light"), not by stack.
- Ownership `product: choose|lead`: the person picks. `decide`: you pick and say why in one line.
- Architecture and stack: follow the person's `architecture` ownership. For `decide`, pick boring, fast tech the team already knows. Good hackathon defaults: Streamlit or Gradio for Python data tools, a single HTML page with plain JavaScript for simple interactive pages, Next.js only if someone on the team already knows it. Avoid anything that needs accounts, paid services or approvals to run.

## Phase 3: design in small pieces

Present the design in sections of about 150 to 250 words. After each section ask: "Does this match what you have in mind?" Fix before moving on.

Sections:
1. Problem and user (2 to 3 sentences, in the domain's words)
2. What the tool does (the demo flow, step by step, as the jury will see it)
3. Data (what goes in, what comes out, where it comes from, licence)
4. How it's built (components and what passes between them, which becomes the interfaces in `$hack-interface`; stack; for T0/T1 a short plain summary here and the technical detail in the doc only)
5. What we fake or leave out (goes on the limits slide later)
6. Who does what (by GitHub username only, no backgrounds or levels in the doc; areas follow what each person wants to work on)
7. Risks and the fallback demo (what we show if the live version breaks: screenshots, a recorded run)

## Phase 4: write it down

Write `docs/design.md` in English using `assets/design-template.md`. Keep it under two pages. Then:
- Add stack, data format and folder layout decisions to `docs/decisions.md` (format in `$hack-team`).
- Mention once that the look can be worked on as a team whenever they like (`$hack-design`), now or once the first screen works.
- Commit on a branch named `docs/design`, open a pull request and offer to merge it right away through `$hack-pr` (asking first) so everyone builds from the same design. Offer `$hack-github` if they don't know how.
- Suggest `$hack-plan` next.

## Stop signs

- The team keeps adding features: ask "which one would you drop if we had to demo in 2 hours?"
- Nobody can describe the user: go back to Phase 1 question 1.
- The idea needs data nobody has: switch to realistic synthetic data and say so, or pick another approach.
