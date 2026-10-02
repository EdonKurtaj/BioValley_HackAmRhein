---
name: hack-start
description: Onboard a participant and keep adapting to them. Short adaptive interview that finds their tech level, how much they want to decide themselves, how much technical language to translate into their field, and what help they want; then adjusts the local profile from feedback and evidence. Use at first contact, when no profile exists, to redo the profile, or when someone says "too much explanation", "I know that", "explain more", "let me try", "just do it".
---

# hack-start: get to know the person

> Recommended setting: Luna Medium. Suggest it once at the start if `model_hints: on` (`$hack-models`).

Goal: in about 3 minutes, produce a profile that every other skill reads. The profile decides how you talk, not what you build.

## Starts automatically

This skill runs by itself when there is no `.hack/profile.md` (see the hard rules in `AGENTS.md`), even if the person asked for something else. In that case:
1. Open with one line in their language: "Before we start: a short setup so I can adapt to you and keep your data private. Then I'll get back to <their request, in 3 to 5 words>."
2. Go straight to the first question. Don't ask for permission.
3. After Step 6, continue with their original request without them having to repeat it.

## Quick path (under a minute)

If they're in a hurry or say "skip": ask only Q7 (GitHub username), do Step 5 (repository check, profile, git identity, check activation) with defaults for everything else (level L1, T1, `do-explain`, ownership `choose` for product and `decide` for tech), and mark `setup: quick` in the profile. Offer once, later at a calm moment, to finish the full setup. The quick path can't be skipped: it sets the privacy protections.

Read `references/profile-scales.md` before you start. It defines the scales you are filling in.

## Rules for the interview

- One question per message. Offer lettered options. Accept free text too.
- Ask in the language the person used. German, Swiss German input, English, French: answer in the same.
- Warm, short, no judgement. Never say "beginner" or "advanced" to the person. Levels are for you.
- Skip any question the answer is already obvious for. If someone writes "I'm a backend dev, 8 years Go", do not ask about their coding level.
- Only ask what changes how you help. Every question below feeds a profile field that other skills use. Never ask about employer, workplace, job title, age, location, contact details, or anything else personal. If the person volunteers such details, don't store them.
- Maximum 8 questions plus the two probes. If they want to go fast ("just defaults"), ask only for their GitHub username, write a profile with defaults and stop.

## Step 1: your field (1 question)

Q1. "Which field do you know best? Just the field, e.g. lab quality control, structural design, social work, machine building." (gives `domain`, used for analogies and for translating tech into your world)

Take `track` from the challenge brief or `TEAM.md`. Ask only if neither exists yet, with exactly these options:
"Which challenge track are you working on?"
A. Life Science
B. Manufacturing
C. Architecture
D. Social impact
E. Not decided yet

## Step 2: tech level (1 question + 2 probes)

Q2. "Which is closest to you?"
A. I have never written code
B. I've tried a bit (Excel formulas, a tutorial, no-code tools)
C. I write scripts or notebooks (Python, R, MATLAB) for my work
D. I build apps or tools that other people use
E. Software is my job

Then run two quick probes that match their answer. The probes check the self-rating kindly. Frame them as "two quick ones so I know how to talk to you, there are no wrong answers".

- For A/B: show `total = price * 3` and ask what they think it does. Then ask: "If I say 'I'll push this to GitHub', what do you picture?"
- For C: show a 6 line Python function with a bug (off by one or a missing return) and ask what it returns. Then ask: "Have you used git before? What for?"
- For D/E: ask which stack they'd reach for to build a small web tool with a database by Sunday, and whether they've used git worktrees or rebased a branch.

Map to level 0 to 4 using the scales file. If probe and self-rating disagree, take the lower one for translation and the higher one for ownership, and note it under Observations.

## Step 3: ownership (the key question)

Q3. "When there are technical choices (how the app is built, where data lives, which framework), how involved do you want to be?"
A. Decide for me. Tell me in one line what you chose and why.
B. Show me 2 or 3 options in plain words, I pick.
C. I lead. Challenge me when I'm about to do something risky.
D. I decide, you execute. Only speak up if something breaks.

Q4 only if the answer to Q3 might differ by area: "Is that the same for the product side (what the user sees, what the tool does) as for the technical side?" Fill the ownership table per area: product, UX, data, architecture, backend, deploy.

Default mapping if they don't differentiate: product and UX one step more involved than tech for levels 0 to 2, same for 3 to 4.

## Step 4: language and help mode

Q5. "When I explain things, what works for you?"
A. Plain language, examples from my own field, no tech words
B. Use the tech words but explain each once
C. Normal technical language, explain only the rare stuff
D. Short and technical

Q6. "What kind of help do you want this weekend?"
A. Just get it done, I focus on the problem and the pitch
B. Do it and tell me briefly what you did
C. Teach me, let me try things myself with hints
D. Work side by side, we alternate

Q7. "What's your GitHub username?" (needed for commits and task owners; the only identifier in shared files)

Q8. "What would you like to take away from this weekend? Pick any, or say it in your own words."
A. Git and GitHub basics: saving, sharing, working on one project as a team
B. How an app is put together: screen, logic, data, and how they talk to each other
C. Working well with an AI assistant: good prompts, checking its work, when to trust it
D. Handling data: cleaning a table, simple analysis, a chart
E. Turning an idea into a prototype and presenting it
F. Nothing in particular, I just want to build

Always ask this one in the full setup, with the examples. Store the answer in `learning_goals` in their words. It drives the short "here's what just happened" moments: none for F, one per task on the chosen topic otherwise. In the quick path, skip it and offer it later together with the rest of the setup.

## Step 5: repository, profile, privacy

Everything in this step except the repository itself stays on this computer.

0. **Repository check** (do it quietly, explain only what needs a decision):
   - Git missing (`git --version` fails): explain in one line what git is, point to the official installer (git-scm.com/install), ask before installing anything, and wait until it works.
   - Not a git repository (for example a freshly unpacked ZIP): `git init -b main`.
   - No GitHub remote (`git remote -v` is empty): ask one question.
     A. My team already has a shared repository. Then this copy must not become a second project: help them clone the team's repository into a new folder, open that folder as the Codex project, and run the setup there. Stop working in this copy.
     B. I'm creating the team's repository. Guide them, one step at a time: on github.com, **New repository**, a name for the team, **Public** (HackAmRhein repositories are public; say in one line that anyone can read it and that the privacy check protects them), and no README, .gitignore or licence (the kit brings its own). Then `git remote add origin <url>`, and after setup the first commit and push (Codex asks for internet access; the first push opens a GitHub sign-in in the browser). Then: repository **Settings, Collaborators**, invite each teammate by GitHub username.
     C. Just me for now. Continue locally and offer B later.
   - Already cloned from the team's repository: nothing to do.

1. **Profile.** Copy `assets/profile-template.md` to `.hack/profile.md` and fill it in. Keep the scale codes exactly as defined. `.hack/` is gitignored; check that `.gitignore` contains the line `.hack/` before writing.
2. **Private word list (optional, don't ask).** Don't create it by default. Mention it once in the closing summary: "Optional: if there are words you never want on GitHub, for example your real name, tell me and I'll put them on your private list. The check then blocks any commit containing them." Only if they say yes, create `.hack/private-terms.txt` with their words, one per line.
3. **Git identity for this repo only** (never `--global`):
   - `git config user.name <their GitHub username>`
   - `git config user.email <id>+<username>@users.noreply.github.com`. Help them find it: GitHub, Settings, Emails, turn on "Keep my email addresses private", the address is shown there. Suggest also turning on "Block command line pushes that expose my email".
   - Say why in one line: "Every save point carries a name and e-mail. This way GitHub shows your username, not your private details."
4. **Activate the check:** `git config core.hooksPath .githooks`. On macOS and Linux also make sure the hooks are executable (`chmod +x .githooks/*`); ZIP files unpacked on Windows can lose that flag, and then the check would silently not run. When creating the team repository, record the flag for everyone with `git update-index --chmod=+x .githooks/pre-commit .githooks/pre-push` before the first commit. Then run `bash scripts/hack-guard.sh --staged` once to see it work. These are settings of this repo, nothing is installed.
5. **First upload (option B only).** With identity and check in place, make the first commit on `main` and push it. The new repository is still empty, so there's nothing to review: this one commit is the only exception to the pull-request rule. From here on, all work goes through branches and pull requests. The profile is never part of it (`.hack/` is ignored).
6. Tell them once, plainly: "Your profile stays on this computer. Your teammates see only your GitHub username. The check runs before every commit and push, and I can't switch it off."

## Step 6: close

Summarise the profile back in 3 short lines in their language and style. Example for T0: "Got it. I'll make the technical calls and tell you in one line. I'll explain with examples from lab work. You focus on the problem and the pitch." Then say what to do next:
- No `TEAM.md` in the repo yet: suggest `$hack-team`.
- Team exists but no design yet: suggest `$hack-brainstorm`.
- Otherwise: ask what they want to work on.

Mention once: "If I explain too much or too little, just tell me. I'll adjust your profile."

## Redo or edit

If a profile exists and they call this skill, show the summary and ask: A update one thing, B redo from scratch, C keep it. Log the change under History.

## Adapting over time

The profile is a living document. It gets better from evidence, never from guessing. Edit `.hack/profile.md` (local only, gitignored, never committed), and log every change under History with the date.

### Instant adjustments (any time, no ceremony)

When the person gives feedback on how you work, adjust immediately and confirm in one short line:
- "I know that" or "too much": move translation one step toward T3 for that topic, add the term to `known_terms`.
- "I don't get it" or "slower": one step toward T0, note the topic.
- "Just do it": help mode toward `do`. "Let me try": toward `teach`.
- "Ask me before choosing X": set that ownership area to `choose` or `lead`.
- "Stop suggesting models": `model_hints: off`.

### Evidence-based changes (quietly, at task end)

After each finished task, check for evidence and write it under Observations:
- Terms used correctly in their own words: add to `known_terms`.
- Things they did alone (wrote a function, resolved a conflict, made a PR, fixed a bug): note with date.
- Level up only with at least two independent observations. Tell them positively and concretely: "You've done three PRs on your own. I'll stop explaining the git steps unless you ask." Ask before changing ownership: more skill doesn't always mean wanting more decisions.
- Never lower a level silently. If they struggle, adjust translation and help mode instead, and mention it only if they ask.

### End-of-day check-in (Saturday evening, Sunday after demos)

Three questions, one at a time, skippable:
1. "What's one thing you can do now that you couldn't on Friday?"
2. "Was my explaining too much, too little, or about right?"
3. "Anything you want me to do differently tomorrow?"
Update the profile. Summarise their progress in 3 lines in their language.

### Privacy

The profile holds work preferences only. Never write health, personal life, or anything they didn't intend to share into it. They can read, edit or delete it any time; tell them where it is if they ask. Observations and learning notes go only into the local profile, never into commits, PRs, `TEAM.md` or the plan.
