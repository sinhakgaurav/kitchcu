FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ckac-common /app/packages/ckac-common
RUN pip install --no-cache-dir /app/packages/ckac-common

COPY services/delivery /app/services/delivery
WORKDIR /app/services/delivery
RUN pip install --no-cache-dir .

EXPOSE 8009

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8009 --reload"]
