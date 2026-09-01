FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/data/logistics.db \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py schema.sql seed.sql ./
COPY tests ./tests

# SQLite file lives here so it can be backed by a named volume in compose.
RUN mkdir -p /data

EXPOSE 8080

# The slim image ships without curl or wget, so the healthcheck uses the
# Python standard library instead.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health', timeout=3).status == 200 else 1)"]

CMD ["python", "app.py"]
