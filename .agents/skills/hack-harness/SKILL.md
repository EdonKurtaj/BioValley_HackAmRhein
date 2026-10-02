---
name: hack-harness
description: Only when the person explicitly asks to use this kit with a different coding agent than Codex (Claude Code, Cursor, GitHub Copilot, Gemini CLI, OpenCode or another). Sets it up on their computer only, without changing anything for the team.
---

# hack-harness: use the kit with another coding agent

> Recommended setting: Luna High.

HackAmRhein supports Codex. Some people prefer another tool, and that's their choice. This skill makes the kit work there **on this person's computer only**. Nothing is committed, nothing changes for teammates, and the kit's files stay the single source: no copies of skills or instructions, only small pointers and links, so nothing drifts.

Run it only when the person asks. Tell them once, plainly: "Codex is what the event supports; with another tool, mentors may not know its details. Everything the kit does through git (privacy check, branches, pull requests, handoffs) works the same."

## 1. Which tool

Ask which one, if it's not clear. Then check the table and the tool's current documentation for its instruction file and skill folder; tools change these often. Never guess a path: look it up or ask the person to check.

| Tool | Reads `AGENTS.md`? | Finds skills in `.agents/skills/`? | What to set up locally |
|---|---|---|---|
| Codex | yes | yes | nothing (default) |
| Claude Code | yes (recent versions, if there's no `CLAUDE.md`) | no, only `.claude/skills/` | `CLAUDE.local.md` with `@AGENTS.md` and `@.hack/harness.md`; links in `.claude/skills/` |
| GitHub Copilot | yes | yes | nothing beyond the notes file |
| OpenCode | yes | yes | nothing beyond the notes file |
| Gemini CLI | not by default (`GEMINI.md`) | yes | its setting to also load `AGENTS.md`, or a local `GEMINI.md` importing it; check its docs |
| Cursor | check its docs | `.cursor/skills/` | links in `.cursor/skills/`; instruction file per its docs |
| Other | check | check | same idea: point to `AGENTS.md`, link the skill folders |

## 2. Set it up (local only)

1. **Keep it out of git for this clone only.** Add every file or folder you create to `.git/info/exclude` (a local list, never shared), for example `CLAUDE.local.md`, `.claude/`, `GEMINI.md`, `.gemini/`, `.cursor/`. Don't touch `.gitignore`.
2. **Notes file** `.hack/harness.md` (already local, `.hack/` is ignored). Write the translations for this tool:
   - Where the kit says `$hack-name`, this tool uses its own way (for example `/hack-name` in Claude Code, Cursor and Copilot, or asking for the skill by name).
   - Where the kit says "Codex", read "this tool". Its permission prompts look different; the rule stays: explain before commands that need the internet, and never switch permissions off altogether.
   - Model names in `$hack-models` are OpenAI's. Map by role: Luna means this tool's small fast model, Sol its main model, Astra its strongest. The same ladder and saving habits apply.
   - Codex app features (Worktree button, Hand off) don't exist here; use the terminal path in `$hack-github` instead.
   - `guessme` must only run when the person types it themselves; never use it on your own.
3. **Instructions:** make the tool load `AGENTS.md` plus the notes file, using its own mechanism (see the table). For Claude Code, `CLAUDE.local.md` contains exactly:
   ```
   @AGENTS.md
   @.hack/harness.md
   ```
4. **Skills:** if the tool doesn't read `.agents/skills/`, link each skill folder into its skill folder. Never copy.
   - macOS and Linux: `ln -s ../../.agents/skills/<name> .claude/skills/<name>` (same for `.cursor/skills/`)
   - Windows: a directory junction, which needs no admin rights: `mklink /J .claude\skills\<name> .agents\skills\<name>` (in `cmd`)
   - For Claude Code, give `guessme` a tiny local wrapper instead of a link: a `.claude/skills/guessme/SKILL.md` with `disable-model-invocation: true` in its frontmatter and one line: follow `.agents/skills/guessme/SKILL.md`. That keeps it explicit-only, as in Codex.
5. **Nothing else changes.** Git hooks, the privacy check, the profile in `.hack/`, handoffs and all team rules are plain files and git; they work in every tool.

## 3. Check it

1. Start the other tool in the project folder and ask it: "What are your project instructions, and which hack skills can you see?" It should describe the four hard rules from `AGENTS.md` and list the hack skills.
2. `git status` shows none of the new files.
3. Make a tiny test commit on a scratch branch: the privacy check should run as usual. Delete the branch afterwards.

Tell the person in one line what was set up and that switching back to Codex needs nothing: the files can stay, or be deleted, without affecting anyone.

## Undo

Delete the created files and links, remove their lines from `.git/info/exclude`, and delete `.hack/harness.md`.
