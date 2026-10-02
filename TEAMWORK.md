# Your team's first project with Codex

A friendly guide for teams of 3 to 5 people.

Codex can help you build things, explain code, and fix problems. You don't need to know all the technical words to get started.

The most useful team rule is simple: **agree on the plan, give each task one owner, and check your work together.**

## 1. Pick one small thing to build

Before everyone starts chatting with Codex, spend 10 to 15 minutes together answering:

- Who are we helping?
- What problem are we solving?
- What should someone be able to do with our project?
- What can we leave out for now?

For example: “Help students find a free study room.”

Choose one person to type while everyone shares ideas. Try this prompt:

> We are a team of [3/4/5] beginners. We have [time available] to build something that helps [people] with [problem]. Help us choose a small, realistic first version. Ask us a few simple questions. Don't write code yet.

Write down your goal in one sentence. Keep it somewhere everyone can see.

## 2. Start from the same project

Have one person help Codex set up a basic version that runs. Everyone should start from that same version.

Already have a project? Ask:

> Explain what this project already does in simple language. What can we reuse for our goal? What is missing? Don't change anything yet.

This saves your team from building the same starting pieces several times.

## 3. Split the work into small jobs

Make a shared list. A document, whiteboard, or task board is enough.

| Job | Who owns it? | Progress |
| --- | --- | --- |
| Make the search screen | Alex | Working on it |
| Add the room information | Sam | Not started |
| Show the matching rooms | Jo | Not started |
| Try the app and list problems | Riley | Not started |
| Prepare the demo | Kim | Not started |

For a team of three, each person can take another job when their first one is finished. You don't need five separate roles.

Keep jobs small: “Show a helpful message when no rooms are found” is easier to share than “Improve the whole app.”

**Before starting a job, put your GitHub username next to it.** Use four simple progress labels: Not started, Working on it, Ready to check, and Done.

Need help splitting things up? Ask:

> Split our project into small jobs for [number] people. Explain when each job is finished and which jobs need something from a teammate first. Point out any jobs that might overlap.

## 4. Give Codex your job and a little context

Each person can use their own Codex chat for their assigned job. Don't assume your chat knows what everyone else is doing.

Copy this and fill in the blanks:

> Our team is building [project]. My job is [one specific job]. My teammates are working on [their jobs]. Please focus on my job. It is finished when [what should work]. If you need to change something a teammate is working on, tell me first. Explain things simply and show me how to check the result.

For example:

> Our team is building a study-room finder. My job is to make the search screen easy to use on a phone. Sam is working on the room information. Please focus on the screen. It is finished when I can enter a location and press Search on a small screen. Explain what you changed and how I can try it.

## 5. Keep everyone's work from getting mixed up

Use one shared home for the code, such as GitHub. Each teammate should work in their own copy of the project.

Ask Codex to help create a **branch** for your job. A branch keeps your changes separate until the team is ready to bring them together.

You can say:

> I'm new to working on a shared project. Help me get the latest team version safely and create a separate branch for my job, called [job name]. Check for any existing work first so nothing gets lost. Explain each step simply.

If two jobs need the same part of the project, talk first. Choose one person to make that shared change, then let the other person continue.

**Separate copies protect your edits. Your shared job list prevents duplicate work. You need both.**

## 6. Try it, share it, and check it together

When Codex finishes, try the result yourself. Click through the feature and check that it does what you asked.

Ask:

> Explain what changed, what you checked, and anything that still needs attention. Give me a short checklist to test this myself.

Then ask a teammate to look at it. Codex can help you open a **pull request**: a way to share your changes for review before adding them to the team version.

> Help me share this change with my team for review. Write a short explanation of what it does and how to try it.

Choose one person to help bring finished work together. After each change is added, check that the full app still works and tell everyone to get the updated version.

## 7. Take a quick team break every 30 to 60 minutes

Ask each other:

- What is ready to check?
- Is anyone stuck?
- Are two people working on the same thing?
- Does our main demo still work?

Put new ideas on a “Later” list so they don't distract everyone from finishing.

Save your final hour for fixing problems and practising the demo. Mark a job Done when it works in the shared project.

## Keep this little checklist nearby

- [ ] We agree on what we are building.
- [ ] Everyone has one clear job to start with.
- [ ] Our shared list shows who is doing what.
- [ ] Each Codex chat knows its task and boundaries.
- [ ] We check with each other before changing shared parts.
- [ ] We try each change before adding it to the team version.
- [ ] We leave time to practise the demo.

You can always tell Codex: **“I'm new to this. Please explain it simply and help me take the next step.”**

**With the HackAmRhein kit,** Codex already works this way: it keeps the shared job list in the plan, each job's progress in the `handoff/` folder, creates a branch per job, and asks before merging anything. Setup is in [HACKAMRHEIN.md](HACKAMRHEIN.md).
