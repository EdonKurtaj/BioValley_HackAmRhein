---
name: hack-ship
description: Finalise and deploy: merge everything, clean the repo, check secrets and data licences, fill in the project README, pick the simplest way to run or host the demo, and tag the version that was shown. Use when someone says "finish", "wrap up", "deploy", "put it online", "make it live", "submit", or on Sunday.
---

# hack-ship: finish cleanly

> Recommended setting: Luna High. Suggest it once at the start if `model_hints: on` (`$hack-models`).

The repository is public from the start. Deploying the app is irreversible enough that you always confirm with the person, whatever their ownership setting.

## 1. Merge what should be shown

There's no code freeze: the team can keep building up to the demo. What matters is that `main` always works.

1. Run `$hack-pr`: every open PR is updated, checked and, after asking, merged, finished, or left for later. Ask the owner.
2. Everyone pulls `main`. Close to the demo, small changes are safer; say so once, then let the team decide.
3. Run the demo flow from `docs/design.md` end to end on a clean start (fresh terminal, fresh browser tab). Fix only what breaks the demo, on a `fix/` branch through `$hack-pr` like everything else (asking before merging). The README update (section 3) goes the same way.

## 2. Safety checks

- Mandatory: `bash scripts/hack-guard.sh --all` scans the whole repo and history for credentials, personal data, local files and private terms. It must print `ok` before tagging or deploying. Fix findings with `$hack-guard`. Add `.env.example` with empty values.
- Data: every dataset in the repo has an entry in `docs/SOURCES.md` with source and licence. No personal, patient or confidential company data in the repo, the repository is public. Synthetic data is labelled as synthetic.
- Licence: the team keeps its IP. Public code without a `LICENSE` file stays all rights reserved; if the team wants others to reuse it, add a licence they chose.

- Mandatory: `bash scripts/doc-check.sh --strict` is clean, formatter, linter and tests pass on `main`, and a final `$hack-review` doc drift sweep is done (README commands run exactly as written, design matches the app, glossary matches the code).

## 3. Project README (in English, for a stranger)

`README.md` is the team's project page; the kit guide lives in `HACKAMRHEIN.md`. Fill in the template's sections and keep its first line linking to the guide. Sections: what it does (2 sentences), who it's for, screenshot or GIF, how to run it (the exact setup and start commands for the project's stack, e.g. `pixi run start`, tested on a fresh clone), data sources, limits, team (GitHub usernames only, unless each person explicitly agrees to their real name). Screenshots must not show names, e-mails or personal data. Keep the design doc and plan in `docs/` for the curious.

## 4. Pick how to run the demo

Offer at most three options, adapted to the stack. The safest demo is running locally on the presenting laptop, with a recorded fallback. Online hosting is a bonus.

| Stack | Easiest hosting | Notes |
|---|---|---|
| Streamlit | Streamlit Community Cloud | Free, deploys from a public GitHub repo. Secrets via its settings page, never in the repo. |
| Gradio or a Python ML demo | Hugging Face Spaces | Free tier, public by default. |
| Static HTML, CSS, JavaScript | GitHub Pages | Settings, Pages, deploy from `main`. Public. |
| Next.js or other web app | Vercel or Netlify | Free tiers, connect the GitHub repo. |
| Anything with a database or heavy compute | Run locally for the demo | Hosting it properly isn't worth the Sunday risk. |

Explain the choice at the person's level. For `deploy: decide`, pick and say why in one line. Hosting makes the app itself reachable by anyone; say that explicitly and get a yes.

Check free-tier limits and current signup steps on the provider's site before promising anything; they change.

## 5. Fallback

Record a 60 to 90 second screen capture of the working demo and keep screenshots of each demo step. Put them where the presenter can reach them offline.

## 6. Tag it

`git tag demo-2026-10-04 && git push --tags`. This marks exactly what was shown, useful after the event.

## 7. Hand over to the pitch

Tell the team: here's what works, here's what's faked. Then `$hack-demo` for the pitch, sources and limits slides.
