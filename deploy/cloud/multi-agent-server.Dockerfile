# Cloud-only image for the shared Multi-Agent Server (bonus B4). Build context: the repository root.
# One uvicorn worker only: the server keeps in-process state (one workflow runs at a time).
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home asd && mkdir /data && chown asd /data
WORKDIR /app/ai-services/multi-agent-server
COPY ai-services/multi-agent-server/requirements.txt .
RUN grep -v '^pytest' requirements.txt > runtime-requirements.txt \
    && pip install --no-cache-dir -r runtime-requirements.txt
COPY ai-services/multi-agent-server/agents.py ai-services/multi-agent-server/checks.py ai-services/multi-agent-server/llm.py ai-services/multi-agent-server/server.py ai-services/multi-agent-server/store.py ai-services/multi-agent-server/workflow.py ./
COPY ai-services/agentic-loop/prompts /app/ai-services/agentic-loop/prompts
ENV MULTI_AGENT_DATA_DIR=/data
USER asd
EXPOSE 5600
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5600", "--workers", "1"]
