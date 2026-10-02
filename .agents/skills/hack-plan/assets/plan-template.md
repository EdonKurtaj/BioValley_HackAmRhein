# Plan

From `docs/design.md`. Status lives in each task's `handoff/` file, not here. Owners by GitHub username only.

Tasks come in chunks. **Parallel**: pick any task in the chunk, one person each, at the same time. **In order**: one after the other, each starts when the one before is merged. A task can start when everything under `Needs` is merged into `main`.

## M1 Walking skeleton: the app starts and shows the demo flow with sample data

### Chunk A · in order
#### T1 Foundation
Owner: @<github-username>
Needs: nothing
Files: <folder layout, interface file, package manager files, theme file, README.md>
Done when: a fresh clone starts with the README commands and shows the demo flow with sample data.
Notes: one task on purpose; merge it early so everyone builds on it (`$hack-build`).

### Chunk B · parallel, from the start (no code needed)
#### T2 <sample data, domain rules, test cases, look, pitch story>
Owner: @<github-username>
Needs: nothing
Files: <e.g. data/sample.csv, docs/rules.md>
Done when: <check anyone can do>

## M2 Core demo flow works

### Chunk C · parallel
#### T3 <what the person will see>
Owner: @<github-username>
Needs: T1
Files: <files it touches, none shared with other tasks in this chunk>
Done when: <check anyone can do on screen, without reading code>
Notes: <interface models it uses, data it needs>

#### T4 <...>
Owner: @<github-username>
Needs: T1, T2
Files: <...>
Done when: <...>

### Chunk D · in order
#### T5 <brings T3 and T4 together>
Owner: @<github-username>
Needs: T3, T4
Files: <...>
Done when: <...>

## M3 Polish, fallback demo, slides

### Chunk E · parallel
#### T6 Fallback demo: screen recording and screenshots of each step
Owner: @<github-username>
Needs: T5
Files: none in the repo
Done when: the presenter can play the recording offline.
