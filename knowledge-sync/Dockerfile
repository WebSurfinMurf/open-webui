FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sync_knowledge.py .
COPY webhook_server.py .

# Default to webhook server mode
ENTRYPOINT ["python", "webhook_server.py"]
