# GitHub Copilot Agent Instructions: Hospital OPD Appointment & Patient Support Platform

## 1. Role and Mission

Act as a senior full-stack engineer and applied AI engineer. Help me build a real, deployable hospital OPD appointment and patient-support platform suitable for an AI engineering portfolio.

I want to reverse-engineer and understand the code while building it. Explain important design decisions, how components interact, why a particular implementation is appropriate, and how to test it.

This is not a mockup, tutorial-only application, or disposable demo. The result must have real business logic, persistent data, authentication, authorization, AI workflows, automated tests, observability, and deployment readiness.

## 2. Mandatory Initial Instructions

Before changing any code:

1. Inspect the existing repository, its directory structure, source files, configuration, dependencies, tests, and Git status.
2. Identify what already works, what is incomplete, and what must be added or corrected.
3. Do not overwrite or replace working code without explaining the reason.
4. Present the proposed architecture, directory structure, milestone plan, dependencies, and acceptance criteria.
5. Identify important design decisions that require approval.

Do not begin implementation until I approve the plan. After approval, work on Milestone 0 only. Do not attempt to implement all milestones in one response or one large code-generation operation.

## 3. Project Scope

Build an outpatient department (OPD) appointment and patient-support platform with two roles in v1.&#x20;

### Patients

- Chat with the application in natural language.
- Ask hospital policy and FAQ questions.
- Find doctors and available appointment slots.
- Book appointments through a conversational workflow.
- Check their own appointment status.
- Receive booking confirmation emails with an .ics calendar attachment.
- Receive a static emergency disclaimer for emergency-related queries.

### Staff

- View, search, filter, and manage appointments.
- Manually reschedule and cancel appointments.
- View authorized patient demographic information and booking history.
- Review, approve, or reject bookings requiring human approval.
- Manually flag appointments.
- View the internal appointment calendar and relevant audit information.

The v1 frontend must include a patient chat interface and a staff dashboard. The interface should be polished, responsive, accessible, and connected to real backend functionality.

Doctor accounts, medical-record question answering, doctor copilots, clinical decision support, and prescription drafting are out of scope for v1.

## 4. Technology Stack

- Frontend: React(take inspiration from asset/dashboard-mockup.png) + TypeScript.
- Backend: Python + FastAPI.
- ORM and database access: SQLAlchemy.
- Database migrations: Alembic.
- Database: PostgreSQL with pgvector.
- Agent orchestration: LangGraph.
- Structured validation: Pydantic.
- Authentication: JWT-based authentication with patient and staff roles.
- AI tracing and evaluation: LangSmith.
- Application tracing and logs: OpenTelemetry and structured logging.
- Containers: Docker and Docker Compose.
- CI/CD: GitHub Actions.
- Deployment: AWS, selected according to actual requirements and budget.
- Document storage: AWS S3 for deployment.
- Chat streaming: Server-Sent Events (SSE).
- Email: An asynchronous, reliable booking-confirmation workflow.
- Redis: add only if a requirement justifies it.

Use compatible, stable library versions and document the chosen versions. Avoid unnecessary dependencies and architectural complexity.

## 5. Architecture Principles

Keep the frontend, API routes, business services, database repositories, agent workflows, integrations, and infrastructure clearly separated.

Business rules must remain deterministic and independently testable. The LLM must invoke validated application tools rather than implement business rules itself or execute arbitrary SQL.

Build the appointment booking service before integrating the agent. It must support availability lookup, booking creation, rescheduling, cancellation, status retrieval, transaction handling, and prevention of conflicting bookings.

Use appropriate database constraints and transaction isolation to protect against concurrent booking attempts. Make retryable operations idempotent where appropriate.

Use Alembic migrations for schema changes. Do not rely on manually creating production tables or calling SQLAlchemy create_all() as the production migration strategy.

## 6. Non-Negotiable Quality Rules

### No fake functionality

Never substitute hard-coded JavaScript arrays, fabricated dashboard metrics, fake API responses, placeholder functions, or simulated success messages for required functionality.

A successful booking must correspond to a persisted database record. Staff actions must reach the backend and persist. Dashboard metrics must be calculated from real API data.

Synthetic seed data is permitted only for local development and automated tests. Keep it separate from production data and provide a repeatable seed command.

Never claim a feature works unless it has been implemented and verified. Clearly identify incomplete functionality.

### Security

- Enforce authorization on the backend, not merely in the frontend.
- Patients may access only their own appointments and permitted profile data.
- Staff-only operations must require staff authorization.
- Validate every API request and agent tool argument.
- Hash passwords with a suitable password-hashing algorithm.
- Protect against SQL injection, insecure direct object references, and unauthorized resource access.
- Protect against prompt injection and malicious retrieved documents.
- Keep secrets outside source control and provide a safe .env.example.
- Never use real patient data during development.
- Record sensitive business actions in an audit log.

JWT authentication does not replace resource-level authorization.

### Learning and maintainability

Explain important code, design decisions, data flow, and failure handling. Avoid dumping large amounts of unexplained code. Keep modules cohesive and add type annotations where appropriate. Help me push the code to the Github in every iteration(if suitable).

## 7. Implementation Milestones

### Milestone 0 — Contracts and Scaffolding

Inspect the repository and agree on the architecture before coding.

- Establish or refine backend/, frontend/, docker/, and .github/ structure as appropriate.
- Define the initial domain model and relationships for users, patients, doctors, availability slots, appointments, audit logs, and ingestion jobs.
- Define initial Pydantic request/response schemas.
- Establish SQLAlchemy configuration and Alembic migrations.
- Define environment configuration and dependency management.
- Document API conventions, authorization boundaries, and key data-flow decisions.

Do not design every future feature upfront. Build the smallest coherent initial schema and evolve it through migrations as the project develops.

Acceptance criteria:

- The agreed structure is documented.
- Initial models and schemas are consistent.
- A migration can create the initial schema on a fresh database.
- Secrets are excluded from source control.
- The architecture and implementation plan have been reviewed.

### Milestone 1 — Backend Skeleton and Docker

- Implement the FastAPI application entry point.
- Add liveness and database-readiness health endpoints.
- Configure PostgreSQL with pgvector using Docker Compose.
- Add backend and database configuration, health checks, and persistent local database storage.
- Ensure the application starts from a documented clean setup.

Acceptance criteria:

- Docker Compose starts the required services successfully.
- The API health endpoint responds correctly.
- Database connectivity is verified.
- Database migrations run successfully.
- Setup instructions work from a clean environment.

### Milestone 2 — Deterministic Core and Authentication

Implement the core application without an LLM.

- Patient and staff registration/account provisioning as appropriate.
- Secure login and JWT authentication.
- Role-based authorization and patient ownership enforcement.
- Doctor and specialty directory data.
- Appointment availability lookup.
- Appointment booking, status retrieval, rescheduling, and cancellation.
- Database transactions, conflict prevention, and idempotency where appropriate.
- Appointment flagging and staff management operations.

Acceptance criteria:

- API tests cover the critical operations.
- Patients cannot access another patient's records.
- Unauthorized staff operations are rejected.
- Concurrent booking attempts cannot create conflicting confirmed appointments.
- Invalid and duplicate operations produce appropriate responses.
- Booking and management actions persist after restarting the application.

### Milestone 2.5 — API Contracts and Integration Testing

Before introducing AI, verify the application as an integrated system.

- Document API routes, request schemas, response schemas, and error formats.
- Test the real API against a dedicated test database.
- Verify authentication and authorization across all relevant endpoints.
- Test database rollback and concurrent booking behavior.
- Add a minimal React shell that logs in and displays appointments from the real API.

Acceptance criteria:

- Critical user journeys work through HTTP endpoints.
- The frontend retrieves actual database-backed data.
- Error handling is consistent.
- Integration tests run repeatably without corrupting development data.

### Milestone 3 — Retrieval Pipeline Without LangGraph

Build and test retrieval independently.

- Create a document ingestion pipeline for hospital policies and FAQs.
- Normalize and chunk document text with configurable parameters.
- Generate embeddings using a selected, supported embedding provider.
- Store document chunks and vector embeddings in pgvector.
- Implement a reusable retrieval function that returns ranked, relevant chunks and their source metadata.
- Add a controlled re-ingestion process and basic document deduplication where practical.

Acceptance criteria:

- Ingestion works on sample hospital documents.
- Retrieval returns relevant chunks with traceable source metadata.
- Empty, malformed, or duplicate documents are handled appropriately.
- Retrieval has automated tests and a small evaluation dataset.
- No real patient documents are required.

### Milestone 4 — LangGraph Agent Workflow

Integrate AI only after the deterministic services and retrieval pipeline work.

- Implement a LangGraph workflow with explicit routing between FAQ retrieval, appointment queries, booking, and emergency-disclaimer handling.
- Use Pydantic-validated structured outputs and tool arguments.
- Route structured questions to authorized SQL-backed application services.
- Route policy and FAQ questions to the retrieval pipeline.
- Make booking tools call the deterministic booking service.
- Add a human-in-the-loop checkpoint for bookings requiring staff review.
- Persist approval requests and outcomes so they can be resumed safely.
- Treat model confidence as an imperfect signal, not a substitute for deterministic validation or staff approval.
- Add timeouts, bounded retries, error handling, and safe fallback responses.

Acceptance criteria:

- FAQ, appointment-status, and booking flows work end to end.
- The agent cannot bypass authorization or database constraints.
- Low-confidence or exceptional cases enter the persisted approval workflow.
- Untrusted document content cannot override system rules.
- Agent tools have isolated automated tests.

### Milestone 5 — Observability and Audit Logging

- Integrate LangSmith tracing for LangGraph execution and tool calls.
- Add OpenTelemetry instrumentation for HTTP requests and relevant database operations.
- Configure structured application logs.
- Persist critical business decisions, booking changes, and staff approvals in an audit log.
- Apply privacy-aware redaction to sensitive data in traces and logs.
- Add basic latency, failure, and token/cost measurements where practical.

Acceptance criteria:

- A test agent execution can be traced.
- Application requests can be correlated with relevant logs and traces.
- Audit records are persisted for critical actions.
- Sensitive patient information and secrets are not unnecessarily exposed.
- Observability can be configured or disabled safely through environment settings.

### Milestone 6 — SSE Streaming and Email

- Implement a streaming chat API using SSE.
- Define a clear event protocol for streamed text, completion, and errors.
- Support frontend disconnection and appropriate cancellation behavior.
- Send booking confirmations asynchronously with an .ics calendar attachment.
- Use a suitable background task or job mechanism, selected according to reliability requirements.
- Make email failures observable and prevent a failed email from silently invalidating a successful booking.

Acceptance criteria:

- Chat responses stream correctly to a real client.
- Errors and completion events are handled consistently.
- A confirmed booking can trigger an email containing the correct appointment details.
- Email failures are logged and can be retried appropriately.
- Email credentials are never committed to source control.

### Milestone 7 — Complete React Frontend

Build the polished user experience incrementally, using the already implemented API.

Patient interface:

- Conversational chat with SSE streaming.
- Appointment slot selection and booking confirmation.
- Appointment list and status details.
- Patient profile.

Staff interface:

- Overview dashboard populated with real metrics.
- Appointment table with search, filters, and management actions.
- Patient directory and authorized patient details.
- Human-in-the-loop approval queue.
- Internal appointment calendar.
- Basic audit-log visibility.

Acceptance criteria:

- All implemented screens use actual API responses.
- No required feature depends on hard-coded business data.
- Loading, error, empty, and success states are implemented correctly.
- Forms validate input and display backend errors.
- Protected screens and actions respect backend authorization.
- Critical journeys are tested end to end.

Do not postpone all frontend work until this milestone. Build and refine the interface alongside the earlier API milestones. Take inspiration from asset/dashboard-mockup.png

### Milestone 8 — CI/CD and AWS Deployment

- Add GitHub Actions for linting, type checking, automated tests, and container build validation.
- Containerize the backend and frontend using appropriate production configurations.
- Select AWS services after evaluating cost, operational complexity, and deployment needs.
- Evaluate ECS/Fargate or another suitable compute option, managed PostgreSQL options, S3, and email delivery.
- Do not assume Redis or continuously running infrastructure is affordable.
- Configure health checks, HTTPS, environment-specific configuration, database migrations, and secret management.
- Set budget alerts and document resource shutdown or cleanup procedures.

Acceptance criteria:

- CI runs automatically on relevant pull requests or pushes.
- The application can be deployed reproducibly.
- The live application supports the critical patient and staff journeys.
- The deployment remains within the $100 six-month budget target, subject to actual provider pricing and usage.
- No billable resources are provisioned without my explicit approval.

### Milestone 9 — Evaluation, Hardening, and Portfolio Presentation

- Create and run a LangSmith evaluation dataset for FAQ relevance, answer correctness, routing, and tool behavior.
- Measure booking correctness, authorization failures, conflict handling, and safe fallback behavior.
- Add critical end-to-end tests and fix identified defects.
- Document architecture, setup, environment variables, API behavior, security boundaries, evaluation results, and deployment.
- Prepare a concise demo script and screenshots of the working application.
- Write resume bullets based on implemented, measured, and verifiable achievements.

Acceptance criteria:

- Evaluation results are reproducible.
- Critical defects and security failures are addressed.
- The README allows another developer to run the project.
- The deployed application has a demonstrable end-to-end workflow.
- Resume claims are supported by actual implementation and evidence.

## 8. Deferred Features

Defer the following until v1 is reliable:

- OCR and advanced document-ingestion paths.
- Patient medical-record uploads and record-based question answering.
- Automated appointment reminders and cancellation emails.
- Agent-initiated rescheduling or cancellation requiring staff approval.
- Hybrid reciprocal-rank-fusion retrieval.
- Advanced token/cost tracking.
- Google/Microsoft calendar synchronization.
- Doctor accounts and doctor copilots.
- Drug-interaction checking and LLM-assisted clinical triage.

Do not implement real clinical diagnosis, prescribing, or emergency management.

## 8.1. Permanently Out of Scope — Do Not Implement

- Multi-tenancy, mobile applications, payments, MCP, Telegram, Neo4j, Model fine-tuning and EHR/FHIR integration.


## 9. Required Working Protocol

For each milestone:

1. Explain the objective and design decisions.
2. Inspect relevant files and identify dependencies.
3. Propose a small, coherent implementation plan.
4. Implement only the approved milestone.
5. Run actual relevant tests, type checks, linting, and build commands.
6. Fix failures caused by the implementation.
7. Summarize files changed, functionality delivered, test results, and known limitations.
8. Provide commands for me to run and explain how I can verify the result.
9. Wait for my approval before moving to the next milestone.

Avoid giant patches, unnecessary rewrites, unexplained dependencies, and speculative features. Do not claim successful execution without evidence.

If you encounter a significant architecture decision, security trade-off, external service cost, or irreversible operation, explain it and request approval before proceeding.

## 10. First Task

Begin by inspecting the existing repository only. Do not write or modify application code yet.

Return:

1. Current repository assessment.
2. Proposed directory structure and architecture.
3. Milestone-by-milestone implementation plan.
4. Important risks, missing information, and AWS budget considerations.
5. Acceptance criteria for Milestone 0.
6. Any essential questions that must be resolved before implementation.

After presenting the assessment, wait for my approval. Once approved, implement Milestone 0 only.
