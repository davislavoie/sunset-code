# Build context must be the repo root (see docker-compose.yml) so that
# `sunset_code` lands as an importable top-level package at /app/sunset_code.
FROM python:3.12-slim

WORKDIR /app

# Install Node.js (required by yt-dlp for YouTube extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY sunset_code/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY sunset_code ./sunset_code
RUN chmod +x ./sunset_code/entrypoint.sh

CMD ["./sunset_code/entrypoint.sh"]
