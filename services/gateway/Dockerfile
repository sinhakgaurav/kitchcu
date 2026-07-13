FROM python:3.12-slim

WORKDIR /app

COPY packages/ckac-common /app/packages/ckac-common
RUN pip install --no-cache-dir /app/packages/ckac-common

COPY services/gateway /app/services/gateway
WORKDIR /app/services/gateway
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
