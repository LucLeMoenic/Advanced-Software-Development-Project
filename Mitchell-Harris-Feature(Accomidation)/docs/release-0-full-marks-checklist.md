# Release 0 Full Marks Checklist

Use this as the working checklist for the integrated group application and report evidence.

## Required Setup

- Shared repository structure in place.
- Shared HTMX `index.html` routes to all five student frontend microservices.
- Shared CSS theme applied across the integrated application.
- Individual frontend, backend/API, and database microservices exist for the assigned feature.
- All required project directories are present.
- Dockerfiles exist for each assigned microservice.
- One shared Docker Compose file runs the integrated app and shared AI services.
- AI-Mode is configured with Ollama and an approved model.

## Functional Software

- Frontend supports search, ranked results, and history.
- Backend orchestrates the search flow and exposes the feature API.
- Database service supports full CRUD.
- Update and delete are user-facing in the UI, not only in the API.
- External API failures are handled gracefully.
- Ranking failures fall back safely.

## Evidence and Logs

- Individual feature plan completed.
- Functional and non-functional requirements documented.
- Risk plan documented.
- Conceptual, ERD, logical, and physical data design artefacts prepared.
- Prompt log updated for meaningful AI-assisted implementation.
- Prompt library contains reusable prompts.
- Review record updated for AI-assisted reviews.
- GitHub commit history shows small, attributable contributions.
- Docker Compose evidence captured.
- GitHub Actions evidence captured.
- Showcase/demo video can show the full integrated flow.

## CI and DevOps

- Student-specific GitHub Actions workflow exists.
- Workflow builds and validates the assigned services only.
- Workflow does not call live Amadeus or Ollama.
- Workflow includes type-checking or linting where applicable.
- Docker build validation is included if practical.

## Report Coverage

- Repository structure.
- Software architecture.
- DevOps pipeline architecture.
- Docker Compose architecture.
- AI workflow diagram and logs.
- GitHub Actions evidence.
- Docker Compose evidence.
- Implementation summary.
- Known issues and limitations.
- Commit logs and contribution logs.
- Showcase video URL.
