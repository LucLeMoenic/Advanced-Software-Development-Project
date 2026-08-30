# Feature Context — AI Accommodation Recommender

Use this file as the shared handoff for any new AI chat about this feature.

## Scope

- Build a single-page accommodation recommender.
- Frontend: Vue 3 + TypeScript.
- Backend: ASP.NET Core Web API for orchestration and AI calls.
- Database: ASP.NET Core Web API + EF Core over SQLite for CRUD only.
- External services: Ollama for ranking, Amadeus for hotel data.

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

- `frontend` only talks to `backend`.
- `backend` talks to `db`, Ollama, and Amadeus.
- `db` owns SQLite and exposes CRUD over HTTP.
- Never open the SQLite file directly from the backend.
- Keep the frontend typed end-to-end with shared interfaces.

## Data Model Summary

- `Chat`: one search session with destination, dates, price range, guest count, preferences, timestamps, and title.
- `Accommodation`: one result within a chat with name, description, price, location, booking link, image URL, rank, explanation, and timestamps.
- Relationship: one chat has many accommodations.
- Rank is unique per chat and cascade delete removes accommodations when a chat is deleted.

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

## Conventions

- Use `<script setup lang="ts">` in Vue components.
- Keep C# services thin and explicit.
- Log search flow stages as `[PLAN]`, `[ACT]`, `[OBSERVE]`, and `[ADAPT]`.
- Fall back safely if Ollama returns malformed JSON.
- Prefer small, reviewable commits.
