FROM python:3.11-slim

WORKDIR /app
COPY student-2/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY student-2/backend/app.py student-2/backend/ai_clients.py student-2/backend/itinerary_review.py ./
COPY student-2/backend/prompts ./prompts
COPY ai-services/agentic-loop/prompts/itinerary-review-v1.txt ai-services/agentic-loop/prompts/itinerary-edit-v1.txt ./prompts/

ENV PORT=8080
ENV ITINERARY_REVIEW_PROMPT=/app/prompts/itinerary-review-v1.txt
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"
CMD ["python", "app.py"]
