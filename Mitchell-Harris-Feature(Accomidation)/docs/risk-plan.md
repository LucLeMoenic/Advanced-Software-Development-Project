# Risk Plan

## Key Risks

- Amadeus test-tier rate limits or outages could break a live demo.
- Ollama could return malformed JSON or incomplete rankings.
- Docker or Compose path quoting could fail because the feature folder contains parentheses.
- The search pipeline could become slow enough to feel unresponsive.
- Data model mistakes could break cascade delete or rank uniqueness.

## Mitigations

- Cache the last successful raw candidate response locally for demo fallback.
- Validate Ollama output and fall back to a naive price sort if parsing fails.
- Quote the feature path everywhere outside Compose, especially in scripts and CI.
- Keep the orchestration flow explicit and log each stage so failures are easy to diagnose.
- Enforce the relationship and unique rank constraint in EF Core, not just in code.
