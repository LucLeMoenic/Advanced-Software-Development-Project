# Release 0 Integrated Software Architecture

The integrated architecture of Group 45's Agentic AI Trip Planning and Travel
Management platform: one shared containerised home page, five
frontend/backend/database microservice sets, and the shared Ollama runtime and
agentic loop. Every element below is defined in the repository-root
`docker-compose.yml` and `shared/vue-frontend/nginx.conf`.

Service-level diagrams for individual features live in each student's
`student-N/docs/architecture.md`.

## Diagram

```mermaid
flowchart TD
    browser["Browser<br/>http://localhost:5100"]
    gw["shared-frontend<br/>Vue home page + nginx gateway<br/>host 5100 : container 80"]

    subgraph s1["Student 1 - Accommodation"]
        f1["student1-frontend<br/>Vue + nginx<br/>host 5101"]
        b1["student1-backend<br/>ASP.NET Core<br/>host 5201"]
        d1["student1-database<br/>ASP.NET Core + EF Core<br/>host 5301"]
        db1[("accommodation.db")]
    end

    subgraph s2["Student 2 - Itinerary"]
        f2["student2-frontend<br/>static + nginx<br/>host 5102"]
        b2["student2-backend<br/>Flask<br/>host 5202"]
        d2["student2-database<br/>Flask<br/>host 5302"]
        db2[("itinerary.db")]
    end

    subgraph s3["Student 3 - Attractions"]
        f3["student3-frontend<br/>HTMX + nginx<br/>host 5103"]
        b3["student3-backend<br/>Flask<br/>host 5203"]
        d3["student3-database<br/>Flask<br/>host 5303"]
        db3[("attractions.db")]
    end

    subgraph s4["Student 4 - Budget"]
        f4["student4-frontend<br/>HTMX + nginx<br/>host 5104"]
        b4["student4-backend<br/>ASP.NET Core<br/>host 5204"]
        d4["student4-database<br/>ASP.NET Core + EF Core<br/>host 5304"]
        db4[("budget.db")]
    end

    subgraph s5["Student 5 - Logistics"]
        f5["student5-frontend<br/>HTMX + nginx<br/>host 5105"]
        b5["student5-backend<br/>Flask<br/>host 5205"]
        d5["student5-database<br/>Flask<br/>host 5305"]
        db5[("logistics.db")]
    end

    subgraph ai["Shared AI services"]
        setup["ollama-model-setup<br/>one-shot: pull and preload tags"]
        ol["ollama<br/>host 11434<br/>volume ollama-data"]
        llm["Approved LLMs<br/>llama3.2:3b, qwen2.5:3b,<br/>qwen2.5-coder:7b"]
        loop["agentic-loop<br/>.NET 8, host 5180<br/>Plan / Act / Observe / Adapt"]
    end

    browser --> gw
    gw -->|"/accommodation/ and /api/"| f1
    gw -->|"/itinerary/ and /itinerary-api/"| f2
    gw -->|"/attractions/ and /attractions-api/"| f3
    gw -->|"/budget/ and /budget-api/"| f4
    gw -->|"/logistics/ and /ui/"| f5

    f1 --> b1 --> d1 --> db1
    f2 --> b2 --> d2 --> db2
    f3 --> b3 --> d3 --> db3
    f4 --> b4 --> d4 --> db4
    f5 --> b5 --> d5 --> db5

    b1 --> ol
    b2 --> ol
    b3 --> ol
    b4 --> ol
    b5 --> ol
    loop --> ol
    setup --> ol
    ol --> llm

    browser -.->|"never"| ol
    b1 -.->|"never opens another db file"| db2
```

The dotted edges state two rules the design enforces: no browser reaches Ollama
directly, and no service opens a SQLite file it does not own.

## Request flow

A user opens `http://localhost:5100`. The `shared-frontend` container serves the
Vue home page, which lists all five features and links to them by relative path.
The same container is also the gateway: its nginx configuration proxies each
feature path to that student's frontend container by Compose DNS name
(`/accommodation/` to `student1-frontend`, `/itinerary/` to `student2-frontend`,
`/attractions/` to `student3-frontend`, `/budget/` to `student4-frontend`,
`/logistics/` to `student5-frontend`), and proxies the matching API prefixes to
the corresponding backend containers. Because every feature is reached through
one origin, no page needs CORS and every URL on a feature page can stay relative.

Inside a feature the path is always the same three hops. The frontend container
serves static assets and proxies its own `/api/` calls to its backend; the
backend owns the public contract, validates input, and calls its database service
over HTTP; the database service is the only process that opens the SQLite file.
For an AI request the backend adds one more hop: it builds a prompt from data it
has already read back from its own database service, then calls
`http://ollama:11434` with the model tag it was configured with, and validates
the model's response before returning it. The marked AI path is therefore
frontend -> backend/API -> Ollama -> LLM; the browser never holds an Ollama URL,
and no model name is hard-coded in calling code - each backend reads its tag from
an environment variable (`APPLICATION_MODEL`, `STUDENT4_MODEL`, or
`STUDENT3_MODEL`).

Every backend that calls Ollama also waits on `ollama-model-setup`, a one-shot
container that pulls any missing model tag into the shared `ollama-data` volume
and preloads the application model before exiting. That ordering is what stops a
first request arriving while a model is still downloading.

The `agentic-loop` container sits beside the application rather than in the
request path. It is a development-time service: it uses two distinct models from
the same Ollama runtime - an implementer for Plan and Act and a reviewer for
Observe - and writes JSON records to `docs/agentic-loop-records/` for a human to
finalise. It serves no application traffic and applies no change to the
repository.

## Database ownership rule

Each SQLite database is owned solely by its own database microservice and is
reached only through that service's HTTP API.

- `student1-database` is the only service that opens `accommodation.db`;
  `student2-database` the only one that opens `itinerary.db`;
  `student3-database` `attractions.db`; `student4-database` `budget.db`;
  `student5-database` `logistics.db`.
- Each file is bind-mounted from that student's `database/storage/` directory, so
  it is visible to exactly one container.
- A backend never imports a SQLite driver for another feature's data. Every read
  and write travels over HTTP to the owning database API, which owns validation
  and schema for its own tables.
- Cross-feature data access, when it is added, must also go through the owning
  service's published API - never through its file, tables, or schema.

This is what makes each feature independently testable (the backend suites mock
HTTP rather than a file) and what keeps schema changes contained to the service
that owns them.
