FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal for the POC (mock extractor needs no OCR libs).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /app/storage

EXPOSE 8020
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
