# Feature Context — AI Accommodation Recommender

Use this file as the shared handoff for any new AI chat about this feature.

## How To Use This File

- Read this first before starting implementation or review work.
- Use it as the compact summary of the high-level design.
- Treat the Release 0 brief and project specifications as the higher-level source of truth when there is a conflict.
- Update the prompt log and review record only when AI meaningfully writes code, infrastructure, or review feedback.

## Scope

- Build one integrated student feature within the Release 0 group application.
- User story: a traveller enters destination, dates, price range, guest count, and free-text preferences, then receives ranked accommodation results with explanations and can revisit search history.
- Frontend: Vue 3 + TypeScript, integrated into the shared HTMX entry page.
- Backend: ASP.NET Core Web API for orchestration, AI calls, and feature API access.
- Database: ASP.NET Core Web API + EF Core over SQLite for CRUD only.
- External services: Ollama for ranking and Amadeus for hotel data.
- Evidence and documentation: prompt log, review record, prompt library, commit history, Docker Compose evidence, GitHub Actions evidence, and report-ready architecture notes.

## Folder Structure

```text
Mitchell-Harris-Feature(Accomidation)/
├── docs/
│   ├── context.md
│   ├── feature-plan.md
│   ├── prompt-log.md
│   ├── prompt-library/
│   ├── requirements.md
│   ├── review-record.md
│   └── risk-plan.md
├── frontend/
├── backend/
└── db/
```

## Architecture Rules

- The feature must fit into the shared group repository and shared deployment.
- The shared HTMX `index.html` is the single entry point for the integrated application.
- The shared CSS theme must be consistent across the integrated app; do not create an isolated visual language for this feature.
- `frontend` only talks to `backend`.
- `backend` talks to `db`, Ollama, and Amadeus.
- `db` owns SQLite and exposes CRUD over HTTP.
- Never open the SQLite file directly from the backend.
- Keep the frontend typed end-to-end with shared interfaces.
- Keep the feature compatible with the shared CSS theme and the group Docker Compose stack.

## Request Flow Summary

1. User submits a search in the frontend.
2. Backend validates and normalises the criteria.
3. Backend creates a chat record in the database service.
4. Backend sources candidate accommodations from Amadeus.
5. Backend persists the candidates through the database API.
6. Backend sends the candidates and search preferences to Ollama.
7. Backend validates the ranking output and falls back safely if the response is malformed.
8. Backend persists rank and explanation updates.
9. Backend returns the ranked results to the frontend.
10. History reloads should fetch persisted chat data rather than rerun the external search pipeline.

## AI Loop Summary

- `[PLAN]`: validate input, decide the search strategy, and create the chat shell.
- `[ACT]`: source accommodations from the external hotel API.
- `[OBSERVE]`: ask Ollama to rank the candidates and explain the ordering.
- `[ADAPT]`: validate the output, persist the final ranking, and fall back to a price-sort ranking if needed.

## Prompt Contract

```text
You are ranking accommodation options for a traveller.

Trip: {destination}, {checkIn} to {checkOut}, {guests} guests, budget {minPrice}-{maxPrice}.
Traveller's own words on what they want: "{preferences}"

Here are the candidate accommodations (JSON):
{candidatesJson}

Rank ALL of them from best (1) to worst fit, considering the free-text preferences
as well as price and description. Respond ONLY with JSON:
[{"id": <int>, "rank": <int>, "reason": "<one short sentence>"}, ...]
```

## Data Model Summary

- `Chat`: one search session with destination, dates, price range, guest count, preferences, timestamps, and title.
- `Accommodation`: one result within a chat with name, description, price, location, booking link, image URL, rank, explanation, and timestamps.
- Relationship: one chat has many accommodations.
- Rank is unique per chat and cascade delete removes accommodations when a chat is deleted.
- EF Core rules: required foreign key, cascade delete, unique index on `(ChatId, Rank)`.

## Deployment Contract

- `accom-frontend` renders the UI and only talks to `accom-backend`.
- `accom-backend` orchestrates search, ranking, and persistence but does not open SQLite directly.
- `accom-db` owns the SQLite file and exposes the CRUD API.
- Ollama and Amadeus are external dependencies called only by the backend.
- The integrated app should run under one shared Docker Compose file.
- Environment variables should inject service endpoints and external credentials.

## API Summary

### Backend-facing DB API

- `POST /api/data/chats`
- `GET /api/data/chats`
- `GET /api/data/chats/{id}`
- `PUT /api/data/chats/{id}`
- `DELETE /api/data/chats/{id}`
- `POST /api/data/chats/{id}/accommodations`
- `PUT /api/data/accommodations/{id}`
- `GET /api/data/accommodations/{id}`
- `DELETE /api/data/accommodations/{id}`

### Frontend-facing backend API

- `POST /api/search`
- `GET /api/chats`
- `GET /api/chats/{id}`
- `PUT /api/chats/{id}`
- `DELETE /api/chats/{id}`

## Release 0 Evidence Targets

- Individual feature plan and risk plan.
- Functional and non-functional requirements for the sprint backlog.
- Conceptual, ERD, logical, and later physical data design artefacts.
- Prompt log entries for meaningful AI-assisted implementation.
- Review record entries for AI-assisted reviews of code or infrastructure.
- GitHub Actions workflow evidence for the student-specific pipeline.
- Docker Compose evidence for the integrated multi-container application.
- Commit history showing small, attributable contributions.
- Report sections covering architecture, workflow, evidence, limitations, and demonstration.

## Conventions

- Use `<script setup lang="ts">` in Vue components.
- Keep C# services thin and explicit.
- Log search flow stages as `[PLAN]`, `[ACT]`, `[OBSERVE]`, and `[ADAPT]`.
- Fall back safely if Ollama returns malformed JSON.
- Prefer small, reviewable commits.
