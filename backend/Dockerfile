FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/ ./
RUN pip install --no-cache-dir -e ".[dev,band]"

COPY data/ ./data/
COPY knowledge_base/ ./knowledge_base/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
