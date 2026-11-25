# Build the existing Roomies interface at a fixed revision. Its source remains
# in this disposable build stage and is not copied into the database repository.
FROM node:22-bookworm-slim AS frontend
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG ROOMIES_REVISION=a294a7e4b2903a76be7d9a4319bf6a57825a8eae
WORKDIR /roomies-source
RUN git init && git remote add origin https://github.com/Jenahh/Roomies.git \
    && git fetch --depth 1 origin "$ROOMIES_REVISION" && git checkout --detach FETCH_HEAD
RUN npm ci --no-audit --no-fund
WORKDIR /integration
COPY build_database_frontend.mjs ./
COPY frontend/ ./frontend/
RUN node build_database_frontend.mjs /roomies-source

FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    ROOMIES_DB_PATH=/data/roomies.sqlite3 ROOMIES_FRONTEND_DIR=/app/web/roomies
WORKDIR /app
COPY requirements-hosting.txt ./
RUN python -m pip install --no-cache-dir -r requirements-hosting.txt
COPY roomies.py chore_api.py request_api.py expanded_api.py ledger_api.py web_preview.py wsgi.py ./
COPY schema.sql expense_extensions.sql seed.sql ./
COPY start_hosted.py gunicorn_conf.py ./
COPY web/ ./web/
COPY --from=frontend /integration/web/roomies/ ./web/roomies/
EXPOSE 8080
CMD ["python", "start_hosted.py"]
