FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY index_docs.py .

ENTRYPOINT ["python", "index_docs.py"]
