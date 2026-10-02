# Codex models for the team (checked 30 September 2026)

Sources: OpenAI's Codex models, pricing, speed, model selection and changelog pages (learn.chatgpt.com/docs/models, /docs/pricing, /codex/agent-configuration/speed, /codex/model-selection, /codex/changelog). The picker in the app is always the truth; update this file if the line-up changes.

## Available on ChatGPT Business

| Model | ID | OpenAI's description | Business usage per 5 h (local messages) | Credits per 1M tokens (input / cached / output) |
|---|---|---|---|---|
| GPT-6 Luna | `gpt-6-luna` | Most efficient model for focused, high-volume tasks, including summarization, extraction and focused coding | 350 to 3,000 | 2.5 / 0.25 / 12.5 |
| GPT-6.1 Sol | `gpt-6.1-sol` | Near-Astra performance for complex work at a lower cost than Astra (released 29 Sept 2026) | 15 to 160 | 50 / 2.5 / 250 |
| GPT-6 Sol | `gpt-6-sol` | Complex coding and agentic workflows (released 22 Sept 2026). Superseded by 6.1 Sol at the same price; not used by the team | 15 to 150 | 50 / 5 / 250 |
| GPT-6 Astra | `gpt-6-astra` | Most capable model for complex work across code, apps and research | 5 to 45 | 250 / 25 / 1,250 |

Weekly limits may also apply. Local messages and cloud chats share the plan's allowance.

## Efforts

Light (Low in the CLI), Medium, High, Extra High, plus Max and Ultra. Luna goes up to Max, not Ultra. Max and Ultra are not used by the team.

OpenAI's own starting points (model selection page): Luna Low for fine-grained edits and simple extraction; Luna Extra High for finding context and constraint-based problems; 6.1 Sol Medium for complex technical work expecting revisions; 6.1 Sol Extra High for polished results from conflicting evidence; Astra Medium for ambitious projects that need broad context.

## Speed

Fast mode works on 6.1 Sol, Astra, 6 Sol and Luna. On a subscription it costs 2.5 times the Standard usage. Ultrafast is not available on Business.

## Retired or retiring (don't pick)

- GPT-5.5: retires from ChatGPT and Codex on 14 October 2026.
- GPT-5.6 Sol, Terra and Luna: the previous generation, no longer listed for Business on the pricing page.
- GPT-5.4 and 5.4 mini: retired 31 August 2026. GPT-5.3-Codex-Spark: retired 14 September 2026.

## Switching

- Desktop app: model and effort control below the message box; **Advanced** for a specific model and effort.
- CLI: `/model` in a session, or `codex -m gpt-6-luna`.
- A personal default is possible in `~/.codex/config.toml` (`model = "gpt-6-luna"`); the kit doesn't change it.
