FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_API_URL=http://student5-database:8080 \
    OLLAMA_URL=http://ollama:11434 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# APPLICATION_MODEL is deliberately not defaulted here: compose passes the
# team-wide tag, and ollama_client.py carries the fallback for bare runs.
COPY app.py db_client.py ollama_client.py advisory.py ui.py ./
COPY templates ./templates
COPY tests ./tests

EXPOSE 8080

# The slim image ships without curl or wget, so the healthcheck uses the
# Python standard library instead.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health', timeout=3).status == 200 else 1)"]

CMD ["python", "app.py"]
