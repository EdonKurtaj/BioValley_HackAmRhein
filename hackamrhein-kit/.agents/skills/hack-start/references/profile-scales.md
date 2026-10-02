# Profile scales

The profile lives in `.hack/profile.md`, local only, never committed. Every hack-* skill reads it and uses these codes. Keep the codes stable so profiles stay compatible across teammates and future projects.

## Level (L0 to L4): what they can do today

| Code | Description | What it means for you |
|---|---|---|
| L0 | Never written code | Never show raw code unless asked. Describe changes by effect ("the upload button now accepts Excel files"). Run all commands yourself. |
| L1 | Tried a bit, formulas, no-code | Show at most tiny snippets with a plain-language line next to them. Run commands yourself, say what they did. |
| L2 | Scripts and notebooks for work | Show relevant code. Explain structure (files, functions, modules) and anything beyond scripting: servers, APIs, state, deployment. |
| L3 | Builds apps others use | Normal collaboration. Explain only unfamiliar stack pieces. |
| L4 | Software professional | Peer. Terse. Focus on tradeoffs and risks. |

Levels go up during the weekend. `$hack-start` (Adapting over time) raises them with evidence.

## Translation (T0 to T3): how much technical language to translate

| Code | Style |
|---|---|
| T0 | No technical words at all. Use analogies from `domain`. "Database" becomes "the lab's sample register" for someone from life science, "the drawing archive" for an architect. |
| T1 | Use the real word, then a one-line gloss in their domain, the first time only. Add the word to `known_terms` once they use it correctly. |
| T2 | Normal technical language. Gloss only rare or stack-specific terms. |
| T3 | Terse, technical, no glosses. |

Always check `known_terms` before glossing. Never explain a term that is already there. Analogies for the four tracks are in `../hack-explain/references/analogies.md`.

## Ownership (per area): who decides

Areas: `product` (what the tool does, for whom), `ux` (what it looks like, flow), `data` (what data, format, where it's stored), `architecture` (how parts fit together, framework), `backend` (server logic, APIs, database), `deploy` (where and how it goes live).

| Code | Behaviour |
|---|---|
| `decide` | You decide. Tell them in one line: what and why, in their language. Log team-relevant decisions in `docs/decisions.md`. |
| `choose` | Offer 2 or 3 options (A/B/C) with one line of consequence each, framed in their world. Recommend one. They pick. |
| `lead` | They propose. You challenge with concrete risks, then do what they chose. |
| `dictate` | Execute their instructions. Only interrupt for things that will break or leak secrets. |

Hard rule for all modes: decisions that affect teammates go through `docs/decisions.md`, and irreversible actions (deleting data, force-pushing, deploying publicly, spending money) are always confirmed with the person, whatever their ownership setting.

## Help mode

| Code | Behaviour |
|---|---|
| `do` | Just do it. Short status. They focus on problem and pitch. |
| `do-explain` | Do it, then 1 to 3 lines on what and why. |
| `teach` | Give a hint or the next step, let them try, then check. Do it for them only when asked or when the clock is tight (after Saturday 20:00 or on Sunday, switch to `do-explain` and say so). |
| `pair` | Alternate. You propose the split ("you write the text for the start page, I wire the upload"). |

## Reply language

`lang`: the language to answer in. Repo artifacts stay English regardless.
