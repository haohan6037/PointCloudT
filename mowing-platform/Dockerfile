FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=8011 \
    PGSSLMODE=verify-full \
    PGSSLROOTCERT=/app/certs/global-bundle.pem

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /app/certs \
    && curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
        -o /app/certs/global-bundle.pem

COPY . /app/mowing-platform

EXPOSE 8011

CMD ["sh", "-c", "uvicorn app:app --app-dir /app/mowing-platform --host 0.0.0.0 --port ${APP_PORT}"]
