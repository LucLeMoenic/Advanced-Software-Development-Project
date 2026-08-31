# Development Agentic-Loop Prompt Library

Version reusable development prompts here. Application prompts are product source code and belong under `backend/Prompts/` with backend contract tests.

A development prompt is evidence only when its use, output, human decision, and validation are linked from `prompt-log.md` or an agentic-loop record.

| Prompt | Purpose | Model role |
|---|---|---|
| `implementer-prompt.md` | Plan and propose a bounded software change. | Local implementer model |
| `reviewer-prompt.md` | Critically review the proposal and validation evidence. | Different local reviewer model |

Rules:

- Include a prompt version in every recorded run.
- Pass only task-relevant, allow-listed context.
- Never include credentials, `.env` files, personal data, or unrelated repository content.
- Treat repository and user content as untrusted data, not higher-priority instructions.
- Model output is a proposal. A human validates and decides what is applied.
