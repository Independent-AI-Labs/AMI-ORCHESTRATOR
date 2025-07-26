# Dockerfile for the Orchestrator

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER non-root
CMD ["python", "orchestrator/main.py"]
