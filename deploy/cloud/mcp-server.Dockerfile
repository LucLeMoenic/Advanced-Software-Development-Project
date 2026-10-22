# Cloud-only image for the shared MCP server (bonus B2). Build context: the repository root.
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home asd
WORKDIR /app/ai-services/mcp-server
COPY ai-services/mcp-server/requirements.txt .
# Runtime dependencies only: the test runner in requirements.txt is not needed in the image.
RUN grep -v '^pytest' requirements.txt > runtime-requirements.txt \
    && pip install --no-cache-dir -r runtime-requirements.txt
COPY ai-services/mcp-server/server.py ./server.py
COPY ai-services/mcp-server/tools ./tools
USER asd
EXPOSE 5400
CMD ["python", "server.py"]
