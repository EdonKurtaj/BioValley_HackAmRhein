---
name: hack-design
description: Work visually as a team to find how the prototype should look and feel: collect references and sketches, compare 2 or 3 quick style directions, then write a one-page design style guide and one theme file the code follows. Use when someone says "design", "look and feel", "style", "colours", "mockup", "sketch", "moodboard", "style guide", shares a screenshot or photo of a sketch, or wants to change the look at any point.
---

# hack-design: from sketches to a style guide

> Recommended setting: Sol Light for comparing directions and writing the guide; Luna High for the theme file and the style sample. Suggest it once at the start if `model_hints: on` (`$hack-models`).

Everyone can contribute here, whatever their background: taste, the people who'll use the tool, and how things look in their field matter more than code.

**Any time, and as often as needed.** The look doesn't have to be settled at the start. From the first task on, all styling sits in one theme file with neutral defaults (see `$hack-build`), so the team can do this session whenever it wants: once the first screen works, when a teammate has an idea, or on Sunday morning to polish for the demo. The first round takes 30 to 45 minutes; later rounds are often 10 minutes on one change. If a style guide already exists, start from it and change only what the team wants to change.

## 1. Collect (10 minutes, everyone; skip for a small change)

Each person brings 2 or 3 references:
- screenshots of apps, websites or dashboards they like (or dislike: that's useful too)
- a photo of a paper sketch or whiteboard drawing of a screen
- something from their field: a lab label, a machine panel, a floor plan, a public-service form

In the desktop app, drag an image into the message box while holding Shift. Ask the person to say what they like about it in one line; point to the part that matters.

Privacy before anything is saved: no faces, no names on sticky notes, no personal or confidential content. Crop or retake the photo. The privacy check can't read images, so you check them by eye before any image is committed.

## 2. Find the directions (10 minutes)

1. Describe what the references have in common and where they pull in different directions, in plain words.
2. Ask the question that matters most for the people who'll use it: where and how do they use it? Examples: gloves and bright lab light need big targets and strong contrast; a factory floor needs readability from a distance; a planner wants dense information; a public service needs plain language and must work for everyone.
3. Propose 2 or 3 directions with a short name and one line each, e.g. "A. Calm and clinical: white, one blue accent, large type. B. Control room: dark, dense, status colours. C. Friendly: warm colours, rounded, lots of space."
4. Make each direction visible. Cheapest and most realistic: a small style sample page in the project's own stack (a few buttons, a card, a table, an alert, a heading, body text) with each direction's colours and type, side by side or switchable. The team looks at it on screen together.
   Image generation (`$imagegen`) is optional, for a mood image or an illustration only. It uses the allowance 3 to 5 times faster than a normal turn, and generated UI text is unreliable, so never use it for screen mockups.
5. The team picks one direction, or mixes ("B's layout with A's colours"). With profile ownership `choose` for UX, the person decides; otherwise the team decides in 2 minutes and you log it.

## 3. Write it down (10 minutes)

1. **Style guide** `docs/style-guide.md` from `assets/style-guide-template.md`. One page: 3 principles in plain words, colour roles, type, spacing, the few components the demo needs, how the app talks (tone of labels and messages), accessibility, and do/don't with the reference images. Refer to colours and sizes by token name, not by value.
2. **One theme file holds the values**, the single home the code reads from:
   - Streamlit: the `[theme]` section of `.streamlit/config.toml`, plus a small CSS file only if needed
   - web (HTML, React, anything with CSS): CSS custom properties in one file, e.g. `src/ui/theme.css`
   - other stacks: their theme or style file
   Record the file's path in the style guide and in `docs/decisions.md`.
3. Check contrast: text against its background at least 4.5:1 (WCAG AA), and never use colour as the only signal (add an icon or a word to red, amber, green).
4. Keep the style sample page as the living reference (for example a hidden `/style` page or `pixi run style`), reading from the theme file.
5. Reference images worth keeping go in `docs/design/`, small and cropped. Commit on a `docs/style-guide` branch and offer to merge through `$hack-pr` (asking first).

## 4. Adapt it over time, keep it true

- UI code uses the tokens from the theme file. No colour, font or spacing values written directly into components.
- A new visual need (a new status, a new component): add the token or rule in the same commit, never an exception on the side.
- The guide is a living document. When the team wants a change (after testing with a real user, a new idea, the demo), change the theme file and the guide together in one commit. Small tweaks just happen; a change of direction gets one line in `docs/decisions.md`. The guide describes, the theme file decides.
- Because every screen reads from the theme file, a change of colours or type updates the whole app at once. Say this to the team: changing the look later is cheap.
- `$hack-review` checks UI changes against the guide.

## Adapting to people

For T0 and T1, talk about what people will see and feel, not about tokens or CSS: "I'll keep all colours in one place, so changing the blue later changes it everywhere." Someone who wants to learn design (learning goal) gets one short "why this works" per decision, for example why contrast matters on a lab screen.
