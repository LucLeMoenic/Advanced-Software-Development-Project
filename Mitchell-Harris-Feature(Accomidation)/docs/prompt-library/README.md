# Development Agentic-Loop Prompt Library

The shared agentic-loop runtime prompts have one authoritative location:

- [`../../../ai-services/agentic-loop/prompts/implementer.md`](../../../ai-services/agentic-loop/prompts/implementer.md)
- [`../../../ai-services/agentic-loop/prompts/reviewer.md`](../../../ai-services/agentic-loop/prompts/reviewer.md)

Do not copy those prompts into this feature folder. The runtime loads the shared files and records their paths and hashes, so duplicate copies weaken rather than improve evidence.

This directory is reserved for future accommodation-specific reusable prompts that are not runtime prompts and not application ranking prompts. Application prompts belong under `backend/Prompts/` with backend contract tests.
