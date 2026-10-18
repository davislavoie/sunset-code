# One image for every Python service: the capture containers, ai-analysis and the dashboard.
# Each compose service picks its command; with none it runs a capture loop. Build context: the repo root.
FROM node:22-slim AS frontend
WORKDIR /build
COPY html_project/frontend/package.json html_project/frontend/package-lock.json ./
RUN npm ci
COPY html_project/frontend ./
RUN npm run build


FROM python:3.12-slim
WORKDIR /app
# Show log output immediately (no buffering), so long steps don't look stuck.
ENV PYTHONUNBUFFERED=1

# Node.js: yt-dlp needs it for YouTube extraction
RUN apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY sunset_code/requirements.txt sunset_code/
COPY ai_analysis/requirements.txt ai_analysis/
COPY html_project/requirements.txt html_project/
RUN pip install --no-cache-dir -r sunset_code/requirements.txt -r ai_analysis/requirements.txt -r html_project/requirements.txt

COPY sunset_code ./sunset_code
COPY ai_analysis ./ai_analysis
COPY html_project ./html_project
COPY --from=frontend /build/dist ./html_project/frontend/dist
RUN chmod +x ./sunset_code/entrypoint.sh

CMD ["./sunset_code/entrypoint.sh"]
