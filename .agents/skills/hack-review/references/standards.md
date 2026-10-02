# Team standards: maintainable code, docs that stay true

These apply to every line written in this repo, by any assistant, for any profile. The profile changes how you explain things to a person. It never lowers these standards.

## Code

### Structure
- **Folder layout is decided once** in `docs/decisions.md` (usually in the first build task) and then followed. Default for a Python data tool:
  ```
  app.py            UI only: layout, inputs, outputs. No business logic.
  src/<project>/interfaces.py   shared data models and contracts (the skeleton)
  src/<project>/    logic, split by responsibility (loading.py, rules.py, scoring.py ...)
  config/           thresholds, rule tables, settings (YAML/JSON/CSV)
  data/             input data and samples (with docs/SOURCES.md entry)
  tests/            one test file per logic module
  ```
  Equivalent split for JavaScript: `src/ui/`, `src/lib/`, `config/`, `tests/`.
- **Separate UI, logic and data.** The rules of the domain must be testable without starting the app.
- **Domain rules as data where possible.** Thresholds, categories, limits and lookup tables go into `config/`, each with a one-line source note. Anyone on the team can read and correct a table; nested code is much harder to check.
- **One responsibility per file and per function.** Split files beyond about 300 lines, functions beyond about 40.

### Interfaces
- The parts of the app talk to each other only through the interface file (`src/<project>/interfaces.py` or `src/interfaces.ts`): shared data models and component contracts. It's the skeleton of the code.
- Features implement and use those contracts. No local copies of models, no raw dicts across part boundaries, no reaching into another part's internals.
- Keep it small. Additive changes happen in the feature branch with a line in `docs/decisions.md`; breaking changes go in a small `iface/` pull request that updates all callers (`$hack-interface`).

### Naming
- **Use the domain's words.** If the team says "batch", "deviation", "release", the code says `batch`, `deviation`, `release`, not `item`, `issue`, `approve`. New domain terms go into `docs/glossary.md` with a one-line definition.
- Names say what something is or does. No `data2`, `tmp`, `helper`, `stuff`, `final_final`.

### Writing code
- **Read before writing.** Search for existing functions before adding a new one. Reuse, don't duplicate.
- **Minimal, targeted changes.** Edit the part that needs changing. Never regenerate or reformat a whole file to change a few lines.
- **Match the existing style** of the file and the project.
- **No speculative abstractions.** Build what the demo needs, simply. Three similar lines are better than a framework nobody asked for.
- **No hard-coded styling.** Colours, fonts and spacing come from the theme file (`$hack-design`), never written directly into components.
- **No magic numbers.** Named constants or config entries, with the source for domain values (`MAX_TEMP_C = 8  # storage limit, source: see docs/glossary.md`).
- **Errors handled at the edges:** file loading, user input, network calls. Clear messages a user understands. No silent `except: pass`.
- **Config and secrets in one place:** `config/` and `.env`. Never scattered through the code.
- **Leave nothing behind:** no commented-out code, no debug prints, no unused imports, files or functions.
- **Comments explain why, not what.** Public functions get a short docstring: purpose, inputs, output.
- **Formatting is automatic.** Python: `ruff` and `pytest` (with pixi as `pixi run fmt`, `lint`, `test`; otherwise in `requirements-dev.txt`). JavaScript: `prettier` and `eslint` as npm scripts. Run them before each commit. The first build task sets this up.

### Dependencies: tidy and reproducible
The stack decides the tool. Whatever the team picks, dependencies are declared in a file that's committed, never installed ad hoc.

- **Python: pixi is preferred, not required.** When the stack is Python, propose pixi once (one line why: identical setup on every laptop). If the team agrees, use it as below. If they decline, or pixi can't be installed, fall back to a project virtual environment (`python -m venv .venv`) with a pinned `requirements.txt`; the project commands then go into the README as plain commands. If the stack isn't Python, pixi doesn't come up at all.
- **With pixi:** one `pixi.toml` describes Python itself, every package and the project's commands; `pixi.lock` pins exact versions so every laptop (macOS, Windows, Linux) gets the same environment. Both files are committed. The environment lives in `.pixi/` (gitignored).
  - Add packages with `pixi add <name>` (conda-forge) or `pixi add --pypi <name>` (PyPI only). Never edit versions by hand.
  - The project's commands are pixi tasks: `pixi run start`, `pixi run test`, `pixi run fmt`, `pixi run lint`. The README shows only these. Nobody has to know which tool is behind them.
- **JavaScript: npm** with a committed `package-lock.json`; commands as `npm run <script>` in `package.json`. Use `npm install <name>`, never global installs for project needs.
- Add only what the demo needs. Every new package is a line in the pull request, not a surprise.
- Never `pip install` into a global or system Python, never global installs for project needs.
- Lock file conflicts after a merge: never hand-edit the lock file. Resolve the manifest (`pixi.toml` or `package.json`), then run `pixi install` or `npm install` to regenerate the lock file, test, and commit.

### Tests
- Every domain rule and calculation gets tests, built from real examples the team provided, including the edge cases they warned about.
- Contract tests (`tests/test_contracts.py`, or `tsc --noEmit` for TypeScript) prove every implementation matches the interfaces.
- Tests run with one command, written in the README (`pixi run test`, `pytest`, `npm test`).
- A red test blocks the commit of that step. Fix or cut, never commit known-broken logic to `main`.

## Documentation: fight drift

Drift kills team projects: docs that describe an app that no longer exists make every teammate's assistant confidently wrong. The rules:

### One home per fact
| Fact | Lives only in |
|---|---|
| What we build and why, demo flow, out of scope | `docs/design.md` |
| Tasks, owners, milestones | `docs/plan.md` |
| Live state of a running task | `handoff/<task>.md` |
| Decisions that affect others | `docs/decisions.md` (append-only) |
| Domain terms | `docs/glossary.md` |
| Data sources and licences | `docs/SOURCES.md` |
| Dependencies and project commands | the stack's manifest: `pixi.toml`, `requirements.txt` or `package.json` (the README only shows how to run) |
| How to install, run, test the project | `README.md` (the team's project page) |
| How to use the kit, setup steps | `HACKAMRHEIN.md` (the participant guide) |
| Visual values (colours, fonts, spacing) | the theme file named in `docs/style-guide.md` |
| How the app should look and why | `docs/style-guide.md` |
| Data models and contracts between parts | the interface file (its docstrings are the docs) |
| How a function works | the code itself (names, docstring, tests) |

Never copy a fact into a second place. Link to its home instead.

### Same-commit rule
A change that alters behaviour, a command, a file path, a config key or a data format updates every doc that mentions it **in the same commit**. Before each commit, search the docs for the names you changed (`git grep <old-name>`).

### Less is more
Don't write docs the code already says. Short true docs beat long stale ones. Delete a section rather than leave it wrong.

### Scope changes update the design
When the team cuts or changes a feature, `docs/design.md` gets updated in that commit (move it to "Out of scope / faked"), and a line goes into `docs/decisions.md`.

### Machine check
`bash scripts/doc-check.sh` finds file paths mentioned in the docs that don't exist, and README run commands that point nowhere. It runs as a warning on every commit and must be clean before shipping (`$hack-ship`).
