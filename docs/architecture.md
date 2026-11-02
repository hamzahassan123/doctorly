# Architecture and implementation notes

## Scope and structure

Doctorly combines a deterministic appointment/authentication backend, a
LangGraph patient-support flow, and a React frontend. PostgreSQL with pgvector
stores application data and FAQ embeddings. See the root README for a project
overview and `docs/DEPLOYMENT.md` for production deployment guidance.

```text
.github/workflows/        # CI checks
alembic/                 # Versioned database schema migrations
docs/                    # Architecture and deployment documentation
frontend/                # React + TypeScript patient/staff application
src/doctorly/
  agents/                 # LangGraph patient-support flow and safety checks
  api/routes/             # FastAPI route handlers
  core/                   # Settings, security, and LLM factory
  db/                    # SQLAlchemy engine and session lifecycle
  models/                # SQLAlchemy entities and domain enums
  schemas/               # Pydantic request/response contracts
  repositories/          # Persistence queries
  services/               # Auth, booking, email, embedding, retrieval
tests/
  unit/
  integration/            # PostgreSQL concurrency and retrieval coverage
```

The source package uses the `src/doctorly` layout. Dockerfiles, local/production
Compose files, and GitHub Actions CI are present. CI builds the backend image
for validation; AWS image publishing and deployment are not configured yet.

## Initial domain

- **User** holds a unique email, Argon2id password hash, active flag, and
  patient/staff role. The current auth service provisions patient accounts;
  trusted staff provisioning is not exposed as a public endpoint.
- **PatientProfile** is one-to-one with a user. Its primary key is also the user
  foreign key, so appointment ownership can be tied to that identity. The
  future account-provisioning service must ensure profiles belong only to
  patient-role users.
- **Doctor** contains directory display name and specialty; doctors do not
  authenticate in v1.
- **AvailabilitySlot** belongs to a doctor and has a timezone-aware interval.
  Exact duplicate intervals for a doctor are rejected, and interval end must
  be after start.
- **Appointment** belongs to a patient profile and an availability slot.
  Only pending-approval and confirmed appointments occupy a slot in the
  database's partial unique index; cancellation releases it. Staff can also
  flag appointments for follow-up.
- **AuditLog** records an actor, target, action, and metadata. Do not put
  passwords, tokens, or unnecessary patient data in its `details`.
- **IngestionJob** records a document-ingestion job's source, state, and
  optional error summary. The ingestion worker and document storage are later
  milestones.

UUID primary keys and timezone-aware datetimes are used throughout. PostgreSQL
is the intended database. The schema prevents duplicate slot intervals and
concurrent active bookings of the same slot. It does not prevent overlapping
slot intervals with different boundaries; availability administration must
avoid creating such intervals until that rule is implemented.

## API and authorization conventions

- Pydantic schemas are the API boundary; ORM objects are not returned directly.
- Appointment creation accepts an availability-slot ID only. The server must
  derive the patient identity from authenticated credentials and must not
  trust a client-supplied patient ID or status.
- Patient endpoints scope reads and writes to the authenticated patient's own
  profile and appointments. Staff-only operations require backend staff
  authorization. Hiding a UI control is not authorization.
- Booking and staff appointment routes map expected domain conflicts to
  explicit HTTP status codes. Unexpected persistence errors are not disguised
  as successful responses.
- Business rules belong in deterministic services. Any future agent must call
  those validated services rather than issuing arbitrary SQL or making
  authorization decisions.

## Persistence and configuration

`DOCTORLY_DATABASE_URL` configures SQLAlchemy and Alembic. Local overrides go
in the ignored `.env`; `.env.example` contains a development-only local URL and
no secret. The initial migration is the schema source of truth. Do not use
`Base.metadata.create_all()` as a production migration strategy.

Appointments reference slots rather than copying slot times. Booking is
transactional and concurrency-safe for a single slot. Staff can cancel or
complete appointments and flag them. Rescheduling and idempotency keys are not
implemented yet.

## API data flow

The intended booking flow is: authenticate the caller, derive their patient
profile on the server, validate the requested slot, then use a deterministic
service and database transaction to create an appointment. Responses use the
Pydantic schemas. Staff operations use staff role checks and write audit
events.

## Current milestone status

Milestones 0–7 have established the database contracts and migrations,
FastAPI/Docker runtime, deterministic authentication and booking, pgvector FAQ
retrieval, LangGraph patient support, model-provider configuration, SSE chat,
optional LangSmith/OpenTelemetry tracing, structured JSON logging, booking
email with an ICS attachment, React patient/staff screens, and GitHub Actions
CI. The CI workflow currently validates and builds the backend image; it does
not push images or deploy AWS resources.

The AWS deployment approach and outstanding production integration work are
documented in `docs/DEPLOYMENT.md`. Provisioning cloud resources requires an
approved account, region, security review, and cost review.

## Milestone 1 runtime

The container image uses Python 3.12, installs dependencies from the frozen
`uv.lock` before copying application source, and runs Uvicorn as the unprivileged
`appuser`. The Compose API service waits for healthy PostgreSQL and Redis
services. Database credentials in Compose default to local-development values
only and must be overridden outside local development. Redis is provisioned as
requested but is not yet consumed by application code.

FastAPI exposes `GET /health` as a liveness response and `GET /health/ready` as
a database readiness check that executes `SELECT 1` and returns HTTP 503 if the
database is unavailable. FastAPI request spans are created through
OpenTelemetry instrumentation. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to an
OTLP/HTTP traces endpoint to export spans; no collector is included in the local
Compose stack, and no telemetry is exported by default.

## Milestone 2 deterministic API

Passwords are hashed with Argon2id through `pwdlib`. Access tokens are signed
with HS256 and contain a user ID subject, issuer, issue time, and expiration;
the role is loaded from the database for every authenticated request so role
changes and inactive accounts take effect immediately. Set
`DOCTORLY_JWT_SECRET_KEY` to a unique secret of at least 32 bytes. There is no
source-controlled signing-key fallback.

Public registration always creates a patient account and profile; it cannot
assign the staff role. Staff accounts must be provisioned through a trusted
administrative path, not public registration. Patient APIs derive ownership
from the bearer token. Staff-only list/update endpoints use backend role
dependencies and record update actions in the audit log.

Implemented HTTP routes are `POST /register`, `POST /login`, `GET /me`,
`GET /doctors`, `GET /slots`, `POST /appointments`, `GET /appointments`,
`GET /staff/appointments`, and
`PATCH /staff/appointments/{appointment_id}`. Registration and booking return
201, expected credential failures return 401, role failures return 403,
unavailable slots and invalid state transitions return 409, and unknown staff
appointment IDs return 404.

Booking checks availability in the service and relies on the database's
partial unique index on active appointments as the concurrency-safe final
guard. An `IntegrityError` is translated to HTTP 409 only when it identifies
the active-slot uniqueness constraint; other persistence errors remain
visible as server errors. Staff status transitions are restricted to
pending-approval -> confirmed/cancelled and confirmed -> cancelled/completed.
Flagging and status changes are audited.

The PostgreSQL concurrency integration test requires `TEST_DATABASE_URL`.
It creates a uniquely named temporary schema and drops that schema on
completion, leaving application tables and data untouched.

## Milestone 3 FAQ retrieval

`FAQDocument` stores synthetic source content, a stable ingestion key, JSON
metadata, and a 384-dimensional embedding from
`sentence-transformers/all-MiniLM-L6-v2`. The Alembic migration enables the
PostgreSQL `vector` extension and creates an HNSW index with
`vector_cosine_ops`. The extension is intentionally retained when this
revision is downgraded because it may be shared by other vector columns.

`EmbeddingService` loads the sentence-transformer locally and returns
normalized vectors. `RetrievalService.search_faq` uses SQLAlchemy's
`cosine_distance`, which emits pgvector's `<=>` operator. `<->` is Euclidean
distance, not cosine distance. `search_documents` reuses the same embedding
and ranking path for another document model and accepts SQLAlchemy filter
expressions, including resource-ownership filters such as `patient_id`.

The FAQ ingestion script reads the hospital knowledge-base JSON array from
`scripts/data/hospital_kb.json`, embeds each title and content, and inserts or
refreshes each record using a slugified title as its stable key. The first run
downloads and caches the model; no model is loaded until embedding is
requested. Retrieval/integration tests require a
`TEST_DATABASE_URL` whose database has the `vector` extension.

## Milestone 4 patient support graph

The compiled LangGraph checks `is_emergency` before invoking the structured
LLM intent router. Emergency matches receive a fixed response from settings
that directs the patient to the Emergency Department, the hospital ER line,
Rescue 1122, and Edhi 115; that response is not generated by an LLM. For
low-confidence routes, symptom/pain language escalates to that fixed emergency
response, while other requests receive a clarification prompt.

The LLM is used only to classify intent using `RouteDecision`. FAQ lookup uses
the existing vector retrieval service and produces an answer solely from the
returned document titles and content. Results beyond the configured cosine
distance threshold receive the fixed helpline fallback. No generative model
answers FAQ questions or provides medical advice. Booking intent only queries
real future available slots and asks the patient to select one; appointment
creation still goes through the deterministic booking API.

`POST /chat` requires an authenticated patient and takes the patient ID from
the verified database user, never from request data. The response is delivered
over Server-Sent Events. The intent router obtains its model from
`doctorly.core.llm.get_llm()`, configured by `LLM_PROVIDER` and `LLM_MODEL`.
Google Gemini is the default and uses `GEMINI_API_KEY` or `GOOGLE_API_KEY`;
other providers require their corresponding LangChain integrations. Direct
emergency handling does not need an LLM key. LangSmith tracing is configurable
and disabled by default; traces can contain prompts and must be treated as
sensitive data.
