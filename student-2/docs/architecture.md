# Itinerary Planner Architecture and Data Design

## Individual Service Architecture

```mermaid
flowchart LR
    U[Traveller] --> H[Shared frontend :5100]
    H -->|/itinerary/| F[Student 2 frontend<br/>nginx and static HTML/CSS/JS]
    F -->|/itinerary-api/*| B[Student 2 backend<br/>Flask orchestration API]
    B -->|HTTP CRUD| D[Student 2 database API<br/>Flask]
    D --> S[(SQLite itinerary.db)]
    B -->|/api/generate| O[Shared Ollama]
    O --> L[Approved application LLM]
```

The browser calls only the backend through the frontend/shared reverse proxies. The backend validates input, controls AI generation and fallback, and requests persistence over HTTP. Only the database service opens SQLite.

## AI Request Flow

```mermaid
sequenceDiagram
    actor Traveller
    participant Frontend
    participant Backend
    participant Ollama
    participant Database
    Traveller->>Frontend: Submit trip details
    Frontend->>Backend: POST /api/trips
    Backend->>Backend: Validate and plan day count
    Backend->>Ollama: Generate constrained JSON
    alt Valid complete response
        Ollama-->>Backend: Two stops per day
    else Timeout, unavailable, or invalid
        Backend->>Backend: Deterministic fallback
    end
    Backend->>Database: Atomic POST /api/data/itineraries
    Database-->>Backend: Persisted trip and stops
    Backend-->>Frontend: Itinerary, generation mode, trace
```

## Conceptual Data Model and ERD

A trip represents one traveller's planning request. A trip contains one or more ordered stops; a stop belongs to exactly one trip.

```mermaid
erDiagram
    TRIPS ||--|{ TRIP_STOPS : contains
    TRIPS {
        integer id PK
        text user_name
        text destination
        text start_date
        text end_date
        real budget
        text interests
        text created_at
        text updated_at
    }
    TRIP_STOPS {
        integer id PK
        integer trip_id FK
        integer day
        text activity
        text notes
        integer sort_order
        text created_at
        text updated_at
    }
```

## Logical and Physical Design

- `trips.id` and `trip_stops.id` are auto-incrementing SQLite integer primary keys.
- `trip_stops.trip_id` is a required foreign key with `ON DELETE CASCADE`.
- `ix_trip_stops_trip_day` orders stop retrieval by trip, day, and sort order.
- Text length, budget, day, and sort-order checks are enforced by both API validation and SQLite constraints.
- UTC timestamps are stored as ISO 8601 text.
- The database file is bind-mounted from `student-2/database/storage` to `/data`.
- Atomic itinerary endpoints validate all input before opening the write sequence and commit trip/stops together.

## Docker Compose Architecture

```mermaid
flowchart TB
    P5100[Host :5100] --> SF[shared-frontend]
    SF --> S2F[student2-frontend :80]
    S2F --> S2B[student2-backend :8080]
    S2B --> S2D[student2-database :8080]
    S2D --> V[Repository-backed SQLite storage]
    S2B --> OL[ollama :11434]
    MS[ollama-model-setup] --> OL
    AL[shared agentic-loop] --> OL
```

## DevOps Pipeline

```mermaid
flowchart LR
    C[Student 2 branch and pull request] --> A[student-2.yml]
    A --> FT[Vitest frontend tests]
    A --> BT[Backend pytest]
    A --> DT[Database pytest]
    A --> CC[Compose configuration validation]
    A --> DB[Build shared and Student 2 images]
    FT --> G[Required checks pass]
    BT --> G
    DT --> G
    CC --> G
    DB --> G
    G --> M[Human-reviewed merge]
```

## Development Agentic Workflow

```mermaid
flowchart LR
    T[Bounded task and allow-listed context] --> P[Implementer model: Plan]
    P --> A[Implementer model: Act]
    A --> O[Distinct reviewer model: Observe]
    O --> D[Bounded revision or rejection: Adapt]
    D --> H[Human validation and final decision]
    H --> R[Finalised evidence record]
```

This development loop is separate from itinerary generation and must be evidenced by the shared runner's finalised record.
