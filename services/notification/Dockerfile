FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ckac-common /app/packages/ckac-common
RUN pip install --no-cache-dir /app/packages/ckac-common

COPY packages/ai-context /app/packages/ai-context
ENV AI_CONTEXT_ROOT=/app/packages/ai-context
RUN pip install --no-cache-dir "pyyaml>=6.0"

COPY services/notification /app/services/notification
WORKDIR /app/services/notification
RUN pip install --no-cache-dir .

EXPOSE 8005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--reload"]
