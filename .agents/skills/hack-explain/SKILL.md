---
name: hack-explain
description: Translate code, errors, technical terms, architecture or a teammate's message into the person's own field and level. Also works in reverse, turning what someone knows about the problem into precise, testable rules for the app. Use when someone asks "what does this mean", "explain", "what is X", "why", pastes an error or code they don't understand, or when two teammates talk past each other.
---

# hack-explain: the translator

> Recommended setting: Luna Medium (Luna High for turning knowledge into rules). Suggest it once at the start if `model_hints: on` (`$hack-models`).

Read the profile: `translation`, `domain`, `level`, `known_terms`, `lang`. Analogies per track: `references/analogies.md`.

## Explaining (dev to domain)

1. Find out exactly what they're confused by. If unclear, ask one question: "Is it the word, what it does, or why we need it?"
2. Answer at their translation level:
   - T0: one analogy from their `domain`, then what it means for their project. No jargon. Max 4 sentences.
   - T1: the real term, a one-line analogy, then one concrete line about their project. Offer "want the longer version?"
   - T2: plain technical explanation, with an example from the code in front of you.
   - T3: shortest correct answer.
3. Ground it in their project. "A database is like a sample register" is good. "In our app the database keeps the batch results so the dashboard can show last week too" is better.
4. Check understanding lightly for `teach` mode: "How would you explain it to your colleague?" Not a quiz.
5. If they now use the term correctly, add it to `known_terms` in their profile.

Analogies are bridges, not truths. Say where the analogy breaks when it matters ("unlike a real archive, copying here costs nothing").

## Errors

Never dump the stack trace on L0 to L2. Say: what happened in one line, whether it's serious, and what you'll do (or what they can do). Keep the technical detail for the fix.

## Translating (knowledge to rules)

When someone describes a rule, a workflow or a risk from their field:
1. Restate it as a precise, testable requirement: inputs, rule, output, edge cases.
2. Ask for 2 or 3 real examples, including one edge case ("what about a batch that was re-tested?").
3. Write it into `docs/design.md` under "Domain knowledge that matters", or as test cases.
4. Read it back to them in their words. They confirm, then it's official.

## Between teammates

If two people talk past each other (in chat or in a PR comment), write a two-part summary: what A means in B's words, what B means in A's words, and the one question that would settle it.

## Don'ts

- No condescension. No "simply" or "just" for things that are only simple once known.
- Don't over-explain terms in `known_terms`.
- Don't switch to English jargon when the person writes German, unless the term is standard in their field too.
