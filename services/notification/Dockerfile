FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ckac-common /app/packages/ckac-common
RUN pip install --no-cache-dir /app/packages/ckac-common

COPY services/notification /app/services/notification
WORKDIR /app/services/notification
RUN pip install --no-cache-dir .

EXPOSE 8005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--reload"]
