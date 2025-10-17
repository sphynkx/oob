# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

## Build deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

## App user
RUN useradd --system --create-home --home-dir /app --shell /usr/sbin/nologin oob
WORKDIR /app

## Install deps first for better caching
COPY install/requirements.txt /app/install/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/install/requirements.txt

## Copy project
COPY . /app

## Expose app port
EXPOSE 8010

## Drop privileges
USER oob

## Default env; override via compose
ENV PORT=8010

## DB schema is applied on start if APPLY_SCHEMA_ON_START=true (db/__init__.py reads install/schema.sql)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "2"]
