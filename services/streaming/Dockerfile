FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ckac-common /app/packages/ckac-common
RUN pip install --no-cache-dir /app/packages/ckac-common

COPY services/streaming /app/services/streaming
WORKDIR /app/services/streaming
RUN pip install --no-cache-dir .

EXPOSE 8012

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8012 --reload"]
