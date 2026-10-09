FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./ai_judge/requirements.txt
RUN pip install --no-cache-dir -r ai_judge/requirements.txt
COPY . ./ai_judge

CMD ["python", "-m", "ai_judge", "watch"]
