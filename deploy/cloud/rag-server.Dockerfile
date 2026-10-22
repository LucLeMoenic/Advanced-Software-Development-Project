# Cloud-only image for the shared RAG server (bonus B3). Build context: the repository root.
# The server finds its prompts at ../agentic-loop/prompts relative to itself, so that directory layout is kept.
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home asd
WORKDIR /app/ai-services/rag-server
COPY ai-services/rag-server/requirements.txt .
RUN grep -v '^pytest' requirements.txt > runtime-requirements.txt \
    && pip install --no-cache-dir -r runtime-requirements.txt
COPY ai-services/rag-server/server.py ai-services/rag-server/confidence.py ai-services/rag-server/generation.py ai-services/rag-server/retrieval.py ./
COPY ai-services/rag-server/knowledge ./knowledge
COPY ai-services/agentic-loop/prompts /app/ai-services/agentic-loop/prompts
USER asd
EXPOSE 5500
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5500"]
