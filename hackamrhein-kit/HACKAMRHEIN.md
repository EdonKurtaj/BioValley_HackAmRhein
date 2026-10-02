# HackAmRhein: build your first prototype with Codex

New to Codex? Start here. You describe an idea in everyday language, and Codex helps create the files, write the code and run your prototype. This kit gives it instructions for guiding you and your team through the weekend: it adapts to how you like to work, handles git and the technical side, and keeps your private data off GitHub.

Allow 20 to 30 minutes for setup, more if your computer needs extra tools. No coding experience needed.

## 1. Install the app

Open the [official OpenAI setup page](https://learn.chatgpt.com/docs/quickstart) and find **Install the ChatGPT desktop app**. Download the version for your system ([Windows page](https://learn.chatgpt.com/docs/windows/windows-app); Mac: open the download and follow the steps; Linux: follow the link on the setup page). This guide uses **Codex inside the ChatGPT desktop app**.

## 2. Sign in and switch to the HackAmRhein workspace

Sign in with your ChatGPT account (create one at [chatgpt.com](https://chatgpt.com) if needed). You don't need an API key. [Sign-in help](https://learn.chatgpt.com/docs/auth).

HackAmRhein gives every participant a ChatGPT Business seat for one month. Accept the workspace invitation with the invited e-mail address, then select the HackAmRhein workspace in the app's account menu, so the event seat is used and not your own. Codex unavailable or a payment request? Ask the organisers before buying anything.

## 3. Create your GitHub account and protect your e-mail

GitHub is where your team keeps and shares its project. Create a free account at [github.com/signup](https://github.com/signup) and verify your e-mail, or sign in. Pick a username you're happy to show: it's the only name the team project shows.

Then: profile picture, **Settings, Emails**. Turn on **Keep my email addresses private** and **Block command line pushes that expose my email**. Keep the address ending in `users.noreply.github.com` handy; Codex uses it during setup. [Email privacy instructions](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).

## 4. Get the project onto your computer

Each team works in **one shared, public project** on GitHub. One person creates it; everyone else joins it. Public means anyone can read it, which is why the kit's privacy check runs before every upload.

**If you create your team's project** (one person per team):
1. Download the kit (hackamrhein-kit.zip) from the HackAmRhein Discord. Unpack it (Windows: right-click, **Extract All**; Mac: double-click) into an easy place such as Documents. Keep the whole folder, including hidden files. Open folders until you see `AGENTS.md`, `README.md` and this guide (`HACKAMRHEIN.md`) side by side: that's the folder you need.
2. Open that folder in Codex (step 5) and send the first message (step 6). Codex notices there's no team project yet and asks you. Choose **"I'm creating the team's repository"**. It guides you through creating an empty **public** repository on GitHub (HackAmRhein projects are public), uploads the kit, and shows you how to invite your teammates (repository **Settings, Collaborators**, by GitHub username).

**If you join your team's project:**
1. Accept the GitHub invitation (by e-mail or on github.com).
2. Create an empty folder, for example Documents/hackamrhein, open it in Codex (step 5) and send: *"Clone <the repository link from GitHub> into this folder."*
3. Open the cloned folder as your Codex project and continue with step 6. Don't work in a separate ZIP copy.

## 5. Open the folder in Codex

In the desktop app, select **Codex**. In the Projects area, add a local project and choose the folder that contains `AGENTS.md`. Start a new chat in that project. [Project help](https://learn.chatgpt.com/docs/projects).

## 6. First message: set up the kit

You don't need a special prompt: write anything in your own words, even just *"Hi, let's get started"*. Codex starts the setup by itself when it doesn't know you yet, and does all of the steps below on its own. If you'd rather spell it out, here's an example of what it covers:

> I am using Codex for the first time. Read AGENTS.md and use $hack-start to set up this kit with me. Explain each step in plain language and ask one question at a time. Check whether Git and the tools the kit needs are installed; guide me through anything missing and ask before installing software. If this folder has no Git repository or no GitHub project yet, help me with that first. Set my GitHub username and noreply e-mail for this project, activate the privacy check, and verify the setup.

What happens:
- A few short questions about you: your field, how much you code, how much you want to decide yourself, how you like explanations, and what you'd like to learn this weekend. There are no wrong answers; it only changes how Codex talks to you. In a hurry? Say **"quick setup"** (under a minute) and finish the rest later.
- Git records your project's save points. If it's missing, Codex points you to the [official installer](https://git-scm.com/install/) and asks before installing anything.
- When a permission pop-up appears (Codex wants to use the internet, for example to upload to GitHub), read what it asks. For git and installing packages in your project, **Allow for this session** is fine. If you're unsure, ask Codex to explain first. Don't switch permissions off altogether.
- Wait until Codex confirms setup is complete. Stuck? Show the error to a mentor.

Your profile and preferences stay on your computer in the hidden `.hack/` folder. It's never uploaded. Your teammates only see your GitHub username.

## 7. Tell Codex what you want to build

New to working as a team with Codex? Read [TEAMWORK.md](TEAMWORK.md) together first (5 minutes). Then, as a team, send: **"Help us set up our team using $hack-team."** Then describe the idea. Copy and fill in:

> I want to build a simple prototype for [who will use it]. Their problem is [what is difficult today]. They should be able to [the main action], and then see [the useful result]. For the first version, use [sample or made-up data]. We need something we can demonstrate by Sunday. Help us clarify the idea and make a small plan. Ask one question at a time and explain choices in plain language.

For example:

> I want to build a tool for volunteers organising a neighbourhood event. They should enter the jobs that need doing and how many people each job needs, then see a checklist of jobs that still need volunteers. Use made-up examples first. Help me choose a small first version and plan it.

When you're happy with the plan:

> Build the first task from our plan. Start with the smallest working version using sample data. Handle the technical steps, explain briefly what you are doing, test it, and show me how to open and try it on my computer.

Use sample data. Keep passwords, API keys and personal or confidential data out of your messages.

## During the weekend

**Talk normally.** Codex picks the right skill. Useful phrases:

| You say | What happens |
|---|---|
| "What can I pick?" | Shows the tasks that are free right now: nobody on them, everything they need is done |
| "Build T3" / "Continue T3" | Works on a task from the plan, or picks up where someone stopped |
| "Explain this" + paste | Explanation in the words of your field |
| "Here's how this works in my field: ..." | Turned into precise rules and test cases for the app |
| "It doesn't work" | Calm, step-by-step debugging; after two failed tries it changes approach |
| "Save this" / "Share my work" | Saves a checkpoint, uploads, opens a pull request |
| "Go over the pull requests" | Updates open work, fixes conflicts, asks you before merging each one |
| "I'm running out" / "I have to go" | Saves a summary in the `handoff/` folder; a new chat continues from it |
| "Let's work on how it looks" + drag in screenshots or photos of sketches (hold Shift) | Compares 2 or 3 style directions on screen and writes a one-page style guide. Works any time, and the look can be changed again later |
| "We're behind, what do we cut?" | Proposes cuts that keep the demo intact |
| "Explain less" / "Explain more" / "Let me try" / "Just do it" | Changes how Codex works with you from now on |
| "How did today go?" | Three quick questions; it adjusts for tomorrow |

**One task, one chat.** Start a new chat when a task is done. Short chats are faster, better and use less of your allowance. Kevin from accounting would say the same in fewer words; `$guessme` what he'd say.

**Pick the model** below the message box (**Advanced** for a specific model and effort). Codex suggests the right one at the start of each task:

| Setting | Use it for |
|---|---|
| GPT-6 Luna, Light | Small clear jobs: git steps, summaries, renaming |
| GPT-6 Luna, High | Most building work. Your default. |
| GPT-6 Luna, Extra High | When Luna missed something |
| GPT-6.1 Sol, Light or Medium | Brainstorming, the first setup task, planning, tricky logic, bugs Luna couldn't fix |
| GPT-6.1 Sol, High or Extra High | The one problem nobody can crack |
| GPT-6 Astra, Medium | Last resort, agreed with the team; uses your allowance very fast |

Sloppy answer: raise the effort. Misunderstood the problem: go up a model. Leave Fast mode off; it uses 2.5 times the allowance. Running low? Switch to Luna: it stretches what's left a long way. Completely out? The allowance is shared across all models, so Luna stops too until it resets after a few hours; meanwhile a teammate takes over, or you work on the pitch.

**Privacy is automatic.** Before every save and upload, a check blocks passwords, keys, e-mail addresses, phone numbers and your local files. If it blocks something, say "fix it". Optional: say "add my real name to my private word list" and it will also block your name.

**Python?** If your team builds in Python, Codex suggests a tool called pixi so everyone gets the same setup. It's optional; say no and it uses a plain Python setup.

**Schedule:** see [hackamrhein.dev/schedule](https://hackamrhein.dev/schedule). Sunday at FHNW Campus Dreispitz: doors 13:00, submission 15:00, demos from 15:30. Codex knows the schedule if you ask, but it won't rush you.

## FAQ

**Codex doesn't know me.** Setup starts by itself in every project without a profile. If it doesn't, type `$hack-start`.

**The skills don't show up when I type `$`.** Check that Codex opened the folder containing `AGENTS.md`. Restart the app after cloning.

**I pushed something private by mistake.** Tell Codex immediately. Keys get replaced first, then cleaned up.

**Can I use another coding agent instead of Codex?** Codex is what HackAmRhein supports, but you can use another tool if you prefer (Claude Code, Cursor, GitHub Copilot, Gemini CLI, OpenCode...). Open the project in it and write: *"Read .agents/skills/hack-harness/SKILL.md and set up this kit for this tool."* It's set up on your computer only; your teammates keep using Codex and nothing changes for them.

**Can I edit the skills?** Yes, they're text files in `.agents/skills/`. Changes affect the whole team, so agree first.

Event information: [hackamrhein.dev](https://hackamrhein.dev).
