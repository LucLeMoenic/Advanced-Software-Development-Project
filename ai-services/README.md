# AI Services

Release 0 shared AI infrastructure:

- `agentic-loop/`: containerised two-model Plan -> Act -> Observe -> Adapt development workflow.
- Ollama: configured in the root `docker-compose.yml`.

Release 1 shared infrastructure (added on `KSS/shared-mcp-rag-setup`; the
group hasn't formally confirmed ownership of these two servers, so treat
that as an assumption until confirmed):

- `mcp-server/`: one shared MCP server, run natively on the host, exposing
  every feature's read-only tools over streamable HTTP on `:5400`. See
  `mcp-server/README.md`.
- `rag-server/`: one shared RAG server, run natively on the host, answering
  `POST /query {feature, question}` with a grounded, cited answer and a
  confidence category. See `rag-server/README.md`.

Neither is a Docker Compose service — same as Ollama and the agentic loop,
per the Release 1 brief. Backends reach them at `MCP_SERVER_URL` /
`RAG_SERVER_URL` (`http://host.docker.internal:5400` / `:5500` from a
container).

Release 2 shared infrastructure:

- `multi-agent-server/`: one shared Multi-Agent Server, run natively on the host on `:5600`. It
  coordinates Planner, Worker and Reviewer agents over caller-supplied evidence and then waits for a
  human decision (approve, correct, partial, reject), with workflow history and a hash-chained audit
  log. Callable from the terminal (`cli.py`) and over HTTP. See `multi-agent-server/README.md`.
  It is not a Docker Compose service.
