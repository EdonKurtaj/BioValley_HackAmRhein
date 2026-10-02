---
name: hack-demo
description: Prepare the Sunday demo: a 3 minute story told by whoever knows the problem best, sources and limits slides, a rehearsal with timing, and likely jury questions. Use when someone mentions pitch, demo, slides, presentation, jury, "sources and limits", or it's Sunday afternoon.
---

# hack-demo: tell it well

> Recommended setting: Sol Light. Suggest it once at the start if `model_hints: on` (`$hack-models`).

The jury sees 3 minutes, not 30 hours. Let whoever knows the problem best tell it.

## The 3 minute shape

1. **The moment it hurts** (30 s): one real person, one real situation. No statistics wall.
2. **What exists today** (15 s): the workaround and why it fails.
3. **Live demo** (90 s): the demo flow from `docs/design.md`, nothing else. Pre-load data, pre-open tabs, zoom the browser to 125 percent.
4. **Why this is hard and why it works** (30 s): the domain knowledge built into it. This is where HackAmRhein teams shine: the thing an outsider would get wrong.
5. **Next step** (15 s): who would use it, what's needed to get there.

Draft the story with the team using the design doc, then write a script in `docs/pitch.md`, in the language of the presentation.

## Sources slide

Built from `docs/SOURCES.md` (no personal data on committed slides; speaker names can be said aloud): every dataset, API, library of note, and AI tools used, with licence. Also say which parts were AI-assisted. Honest and short.

## Limits slide

From the design's "Out of scope / faked" section and anything cut on Sunday: what is simulated, what data is synthetic, what wasn't tested, known failure cases, what it must not be used for yet (especially for health, safety or public-sector use). Juries trust teams that name their limits.

## Rehearse

Run the whole thing twice with a timer. After the first run, cut 20 percent. Decide who clicks and who talks. Test the fallback video once.

## Likely jury questions (prepare one-line answers)

- Who exactly would use this, and what do they do today?
- What did you fake?
- Where does the data come from, and can you use it?
- What would it take to run this for real (cost, regulation, validation)?
- What was the hardest part?
- What did each of you contribute? (Everyone should be able to answer this about themselves.)

## Adapting to people

Stage fright is normal. Offer to write speaker notes in the presenter's language. For people who asked to learn presenting in `learning_goals`, give them one concrete tip after the rehearsal, not ten.
