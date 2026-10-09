# Build context: the repo root (see docker-compose.ai.yml), so the judge can import
# the capture pipeline's own functions (sunset_code) for re-ranking, unchanged.
FROM python:3.12-slim

WORKDIR /app
# Show log output immediately (no buffering), so long steps don't look stuck.
ENV PYTHONUNBUFFERED=1
COPY sunset_code/requirements.txt sunset_code/requirements.txt
COPY ai_judge/requirements.txt ai_judge/requirements.txt
RUN pip install --no-cache-dir -r sunset_code/requirements.txt -r ai_judge/requirements.txt

COPY sunset_code ./sunset_code
COPY ai_judge ./ai_judge

CMD ["python", "-m", "ai_judge", "watch"]
