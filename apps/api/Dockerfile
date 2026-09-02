FROM python:3.12-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends --yes libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn evidence_parse.main:app --host 0.0.0.0 --port 8000"]
