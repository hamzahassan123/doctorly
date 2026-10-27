# Architecture and initial contracts

## Scope and structure

The project is being built incrementally. Milestone 0 established database
models, Pydantic contracts, configuration, and migrations. Milestone 1 added
the FastAPI runtime and container setup. Milestone 2 adds authentication,
authorization, and deterministic appointment operations; no AI workflows are
implemented.

```text
.github/                 # GitHub automation in a later milestone
alembic/                 # Versioned database schema migrations
docs/                    # Architecture, API conventions, and decisions
frontend/                # React + TypeScript client (scaffold only in M0)
src/doctorly/
  core/                  # Environment-backed settings
  db/                    # SQLAlchemy engine and session lifecycle
  models/                # SQLAlchemy entities and domain enums
  schemas/               # Pydantic request/response contracts
  api/routes/            # FastAPI route handlers
  repositories/          # Persistence queries
  services/              # Deterministic business rules
  agents/                # LangGraph workflows (later)
  integrations/          # External service adapters (later)
tests/
  unit/
  integration/           # Database/API integration coverage (later)
docker/                  # Container setup (Milestone 1)
```

The current source package uses the existing `src/doctorly` layout. Docker and
the executable frontend are intentionally deferred until their planned
milestones rather than added as empty or nonfunctional applications.

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

## Milestone sequence

1. Contracts and scaffolding (complete).
2. FastAPI health-check skeleton, OpenTelemetry request instrumentation, and
   PostgreSQL/pgvector + Redis Compose setup (complete).
3. Deterministic appointment services and authentication/authorization
   (complete).
4. HTTP integration coverage and a real-data frontend shell (next).
5. Document ingestion and retrieval without an agent.
6. Validated LangGraph workflow over the established services.
7. Privacy-aware tracing, structured logging, and audit coverage.
8. SSE chat and reliable asynchronous booking email.
9. Complete patient and staff React experiences.
10. CI/CD and a cost-reviewed AWS deployment proposal.
11. Evaluation, hardening, and portfolio documentation.

No AWS resources should be provisioned without explicit approval and a
cost review against the project's six-month budget target.

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
