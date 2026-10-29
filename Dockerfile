# syntax=docker/dockerfile:1
###############
# FRONTEND    #
###############

FROM node:24-alpine AS frontend

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi && \
    npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build


###########
# BUILDER #
###########

FROM python:3.12-slim-bookworm AS builder

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.lock .
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.lock


#########
# FINAL #
#########

FROM python:3.12-slim-bookworm

# Runtime deps for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set up directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/ase
RUN mkdir -p $APP_HOME/staticfiles/frontend
WORKDIR $APP_HOME

# Install dependencies
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.lock .
RUN pip install --no-cache --no-index /wheels/* && \
    rm -rf /wheels

# Copy project
COPY . $APP_HOME

# Copy frontend build (Vite outputs to ../staticfiles/frontend relative to frontend/)
COPY --from=frontend /app/staticfiles/frontend $APP_HOME/staticfiles/frontend

# Collect static files (Django legacy + React)
RUN cp -r ${APP_HOME}/app/static/* ${APP_HOME}/staticfiles/ 2>/dev/null || true

# Make entrypoint executable
COPY entrypoint.sh $APP_HOME/entrypoint.sh
RUN chmod +x $APP_HOME/entrypoint.sh

# Set ownership
RUN chown -R app:app $APP_HOME

USER app

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
