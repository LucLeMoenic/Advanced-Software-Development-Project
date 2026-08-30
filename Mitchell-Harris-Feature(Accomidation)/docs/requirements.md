# Requirements

## Functional Requirements

- User can search by destination, check-in date, check-out date, price range, guest count, and free-text preferences.
- User receives a ranked list of accommodations with short explanations for the ranking.
- User can view past searches in a history panel.
- User can reload a past search without rerunning the external sourcing and ranking pipeline.
- User can rename a past search.
- User can delete a past search and its accommodations.
- Search results are persisted so the history can be revisited.
- The feature is integrated into the shared Release 0 application through the shared HTMX entry point and shared CSS theme.
- The feature can be demonstrated through the frontend, backend/API, database, Docker Compose, and GitHub Actions evidence required by the brief.

## Non-Functional Requirements

- The ranking pipeline must degrade gracefully if Ollama returns malformed output.
- The feature should remain usable if the external source is slow or temporarily unavailable.
- Search should complete in a reasonable time even though it includes external API calls.
- The database should enforce the required parent-child relationship and prevent duplicate ranks within a chat.
- The frontend, backend, and database should remain cleanly separated by responsibility.
- All public-facing DTOs should be typed consistently across the frontend and backend.
- The application should remain compatible with the shared group repository layout and student-specific GitHub Actions workflow structure.
- The feature should produce report-ready evidence for architecture diagrams, logs, commit history, and known limitations.
- The UI should stay usable on desktop and mobile within the shared integrated app.
