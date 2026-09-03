# Self-hosting and deployment

OCRWorkbench is local-first and can run with Docker Compose. The default
configuration is intended for a trusted development machine; review these
boundaries before exposing it to a network.

## Required production settings

- Set `EVIDENCE_PARSE_AUTH_REQUIRED=true`.
- Set `EVIDENCE_PARSE_API_KEYS` from a secret manager, not a committed file.
- Replace the default PostgreSQL password.
- Set `EVIDENCE_PARSE_CORS_ORIGINS` to the exact web origins that need access.
- Terminate TLS at a trusted reverse proxy and do not expose PostgreSQL publicly.
- Back up the PostgreSQL volume and test restoration before relying on it.

Generate API keys with a cryptographically secure secret generator. Multiple
comma-separated keys are accepted so rotation can happen without downtime:

1. add the new key while keeping the old key;
2. update clients and the browser workbench;
3. remove the old key and restart the API.

The API compares keys in constant time and never writes them to application
records. The browser workbench keeps its optional key only in component memory;
refreshing the page clears it.

## Health and orchestration

- `/health/live` proves the process can answer HTTP.
- `/health/ready` proves the configured database accepts a query.
- `/health` retains the versioned compatibility response.

Docker Compose waits for PostgreSQL readiness, applies all Alembic migrations,
then starts the API and web services as non-root users. CI builds both images,
starts the complete stack, checks both HTTP surfaces, and verifies container UIDs.

## Current scaling boundary

Batch status is persisted, but source bytes and execution remain in the API
process because no document-retention policy has been chosen. A process restart
can interrupt an active batch. Before horizontal scaling, move execution to a
durable external queue and define encrypted source storage, retention, retry,
and dead-letter policies.

API keys provide service-level protection, not user accounts, organizations,
roles, or row-level tenant isolation. Put a trusted identity-aware gateway in
front of the service when individual user identity is required.
