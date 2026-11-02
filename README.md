# Doctorly

Doctorly is an outpatient appointment and patient-support platform. It combines
a deterministic FastAPI backend for authentication and booking with a
LangGraph-based patient-support agent, a React patient/staff frontend, and
PostgreSQL with pgvector for policy retrieval.

> **Development and privacy notice:** this is a project under active
> development, not a certified clinical system. Do not enter real patient
> information or rely on it for medical advice or emergency response. The
> emergency response directs users to local emergency care; it does not replace
> emergency services.

## Architecture

```text
Patient / staff browser
        │
        ▼
React + TypeScript frontend
        │ JSON API + Server-Sent Events
        ▼
FastAPI ─────────────── LangGraph patient-support flow
   │                     ├─ emergency phrase guardrail
   │                     ├─ configurable LLM intent routing
   │                     ├─ pgvector FAQ retrieval
   │                     └─ appointment availability lookup
   ├─ deterministic auth, authorization, booking, audit
   ├─ SQLAlchemy + Alembic
   └─ async SMTP appointment confirmation with ICS invite
        │
        ▼
PostgreSQL + pgvector                 Redis
```

- **API:** FastAPI, Pydantic, SQLAlchemy, Alembic, and JWT bearer
  authentication. Booking rules and staff authorization are enforced in the
  backend, not by the frontend.
- **Patient support:** LangGraph checks emergency phrases before LLM routing.
  FAQ answers are sourced from retrieved hospital knowledge-base documents;
  they are not generated from the model's general knowledge. Appointment
  intent lists real available database slots.
- **Retrieval:** `sentence-transformers` generates 384-dimensional
  `all-MiniLM-L6-v2` embeddings. PostgreSQL/pgvector performs cosine retrieval
  and uses an HNSW index.
- **Web client:** React, TypeScript, Vite, Tailwind CSS, TanStack Query, and
  React Router. Patient routes cover sign-in, registration, chat, and booking;
  staff routes provide protected appointment management.
- **Operations:** Dockerfiles, local and production Compose definitions, GitHub
  Actions CI, structured JSON logs, optional OpenTelemetry export, and optional
  LangSmith tracing.

See [docs/architecture.md](docs/architecture.md) for additional domain and API
details, and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the AWS deployment
plan.

## Repository layout

```text
alembic/                    Database migrations
docs/                       Architecture and operations documentation
frontend/                   React/Vite patient and staff application
scripts/                    FAQ ingestion utilities and source data
src/doctorly/
  agents/                   LangGraph state, nodes, graph, and safety checks
  api/routes/               FastAPI route handlers
  core/                     Settings, LLM factory, and security
  db/                       SQLAlchemy engine and session
  models/                   ORM entities and enums
  repositories/             Persistence queries
  schemas/                  API contracts
  services/                 Auth, bookings, email, embeddings, retrieval
tests/
  unit/                     Unit and API workflow tests
  integration/              PostgreSQL booking and retrieval tests
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm (frontend)
- Docker Compose and sufficient disk space for local PostgreSQL and the CPU
  PyTorch / sentence-transformers dependencies, or an externally reachable
  PostgreSQL instance with pgvector and Redis

## Local development

### Backend and supporting services

1. Copy the example environment file and replace the development signing key.
   The example contains dummy values only; never use them outside a disposable
   local environment.

   ```powershell
   Copy-Item .env.example .env
   uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Put the generated value in `DOCTORLY_JWT_SECRET_KEY` in `.env`. The key must
   contain at least 32 bytes. Keep `.env` private and untracked.

2. Start PostgreSQL/pgvector and Redis:

   ```powershell
   docker compose up -d db redis
   ```

3. Install backend and development dependencies, migrate the database, and
   start the API:

   ```powershell
   uv sync --group dev
   uv run alembic upgrade head
   uv run uvicorn doctorly.main:app --reload
   ```

   The API is available at `http://localhost:8000`. Check `GET /health` for
   liveness and `GET /health/ready` for database readiness. API docs are at
   `http://localhost:8000/docs`.

   To use the full local stack instead, `docker compose up --build` starts the
   API, database, and Redis. Apply migrations with
   `docker compose exec api alembic upgrade head`.

4. Configure an LLM provider for non-emergency chat. Defaults are
   `LLM_PROVIDER=google` and `LLM_MODEL=gemini-1.5-flash`; supply
   `GEMINI_API_KEY` or `GOOGLE_API_KEY`. Emergency phrase detection and the
   fixed emergency response do not require a provider key. OpenAI and Groq
   keys are also represented in the settings, but their LangChain integrations
   must be added before selecting those providers.

5. To seed the hospital FAQ knowledge base, after migrations:

   ```powershell
   uv run python scripts/ingest_faqs.py
   ```

   This reads `scripts/data/hospital_kb.json`, embeds the title and content, and
   upserts documents by their stable title-derived key. The first run may
   download the embedding model and require substantial disk space.

### Frontend

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The frontend currently calls
`http://localhost:8000` directly; the API CORS policy allows this local origin.
See [frontend/README.md](frontend/README.md) for the frontend feature summary.

## Tests

Run unit and API workflow tests with:

```powershell
uv sync --group dev
uv run pytest
```

PostgreSQL integration tests are skipped unless `TEST_DATABASE_URL` is set.
They create uniquely named temporary schemas and drop only those schemas when
finished. For local Docker Compose PostgreSQL, use:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://doctorly:doctorly@localhost:5432/doctorly"
uv run alembic upgrade head
uv run pytest
Remove-Item Env:TEST_DATABASE_URL
```

The test database user needs permission to create and drop schemas. The
retrieval integration test additionally requires the pgvector extension; the
Alembic migrations install it. Do not point integration tests at production
data.

Frontend checks:

```powershell
Set-Location frontend
npm ci
npm run lint
npm run build
```

GitHub Actions runs backend tests with a temporary PostgreSQL/pgvector service,
then runs the frontend lint/build checks and validates the backend Docker
image build.

## API capabilities

Public and authenticated routes include:

| Route | Purpose |
|---|---|
| `POST /register`, `POST /login`, `GET /me` | Patient account and bearer-token auth |
| `GET /doctors`, `GET /slots` | Active doctors and available appointment slots |
| `POST /appointments`, `GET /appointments` | Book a slot and list the current patient's appointments |
| `GET /staff/appointments` | Staff-only appointment queue |
| `PATCH /staff/appointments/{appointment_id}` | Staff-only status/flag updates |
| `POST /chat` | Authenticated patient-support stream |
| `GET /health`, `GET /health/ready` | Liveness and database readiness |

Public registration creates patient accounts only. Staff identities must be
provisioned through a trusted administrative process. Database migrations are
explicit; application startup does not automatically alter the schema.

## Configuration and security

`.env.example` documents the supported local, LLM, tracing, email, and AWS
deployment variables. Copy it to an ignored `.env` for local work. For AWS,
store runtime secrets in AWS Secrets Manager or Systems Manager Parameter Store
and grant access through IAM roles. Do not commit credentials, real patient
data, or populated environment files. Review
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) before deploying.
