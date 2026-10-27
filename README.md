# Doctorly

Doctorly is a hospital outpatient appointment and patient-support platform.
The backend currently supports patient registration/login, doctor and slot
lookup, patient-owned appointment booking/listing, and protected staff
appointment listing/updates. AI workflows, frontend screens, and deployment
infrastructure have not been implemented yet.

## Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Docker with Docker Compose (for the local stack)

## Local setup

1. Start the local API, PostgreSQL/pgvector, and Redis services:

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   # Generate a local signing secret and add it to the ignored .env file.
   uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
   docker compose up --build
   ```

   The command prints a random signing secret; copy it into the
   `DOCTORLY_JWT_SECRET_KEY` line in `.env` before starting Compose. The API
   waits for PostgreSQL and Redis health checks before starting. Override
   `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` for local use as
   needed. Authentication endpoints return HTTP 503 until a signing secret of
   at least 32 bytes is configured. Never use the database defaults in
   production.

2. In a second terminal, apply the schema migration:

   ```powershell
   docker compose exec api alembic upgrade head
   ```

3. Check the API liveness and database readiness endpoints:

   ```powershell
   Invoke-RestMethod http://localhost:8000/health
   Invoke-RestMethod http://localhost:8000/health/ready
   ```

4. To run tests on the host, install the declared dependencies and dev group:

   ```powershell
   uv sync --group dev
   uv run pytest
   ```

For the PostgreSQL concurrency integration test, set `TEST_DATABASE_URL` to
the running local PostgreSQL URL before running tests. It creates and drops
only a temporary, uniquely named schema; it does not alter application tables.
For example, with the default local Compose database in PowerShell:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://doctorly:doctorly@localhost:5432/doctorly"
uv run pytest
Remove-Item Env:TEST_DATABASE_URL
```

`/health` is a liveness check. `/health/ready` executes a database query and
returns HTTP 503 when PostgreSQL is unavailable. The database container health
check also gates API startup. Database migrations are applied explicitly using
the command above, not automatically during API startup.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the current model,
authorization boundaries, API conventions, migration strategy, and planned
repository structure.

## Current limitations

The API also exposes health checks. Staff accounts are not created by public
registration and must be provisioned through a trusted administrative path.
No real patient data should be used.