# AWS deployment guide

This guide describes a production-oriented AWS path for Doctorly. The
repository's GitHub Actions workflow currently runs tests and builds the
backend image for validation; it does **not** yet authenticate to AWS, push
images to ECR, or deploy services. Those release steps must be added after
the AWS account, region, domains, and cost limits are chosen.

## Recommended topology

```text
Browser
  ├─ HTTPS ── Amplify Hosting or Vercel (React static frontend)
  └─ HTTPS ── public API URL
                 └─ App Runner (existing customers only)
                    or ECS Express Mode / ECS Fargate (new AWS customers)
                       ├─ private VPC connection ── RDS for PostgreSQL + pgvector
                       ├─ private VPC connection ── ElastiCache for Redis
                       └─ Secrets Manager / Parameter Store

GitHub Actions ── GitHub OIDC ── IAM deploy role ── ECR
                                              └── image deploy/release
```

### Compute

The original recommendation was AWS App Runner for the FastAPI container.
**AWS App Runner is no longer open to new customers.** Existing App Runner
customers can continue using it; AWS recommends ECS Express Mode for new
customers. ECS Express Mode provisions an ECS/Fargate service with a load
balancer, scaling, and networking from a container image. For more control,
use ECS on Fargate directly.

- Use the backend image built from the repository root `Dockerfile`.
- Configure the service to listen on container port `8000`.
- Set the service health check to `GET /health`. Use `/health/ready` as a
  database-aware readiness check where the platform supports it.
- Put the service in a VPC configuration that can reach the private RDS and
  ElastiCache endpoints. Keep the database and cache private.
- Use a custom HTTPS API domain and an ACM-managed certificate/load balancer
  as appropriate for the selected compute service.

If you already operate App Runner, configure its VPC egress connector for the
private database/cache subnets and configure the service's ECR access role to
pull the backend image. For new AWS accounts, prefer ECS Express Mode or ECS
Fargate rather than planning around App Runner.

Official references:
[App Runner availability](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html),
[ECS Express Mode](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html).

### Database and cache

- Create an Amazon RDS for PostgreSQL instance in private subnets, with
  automated backups, encryption at rest, deletion protection, and a security
  group that accepts PostgreSQL traffic only from the backend service.
- Select an RDS PostgreSQL engine version that supports the `vector` extension
  and the HNSW index features used by the migrations. Confirm the extension
  version against the current AWS supported-extension list before provisioning.
- Apply schema updates with `alembic upgrade head` before deploying application
  code that depends on a new schema. The migrations create the pgvector
  extension, 384-dimensional FAQ embedding column, and cosine HNSW index.
- Do not use the development SQLite database or the local Compose database as
  production storage. Keep RDS off the public internet.
- Create an ElastiCache Redis deployment only if the application starts
  consuming Redis. Redis is currently included in Compose but is not used by
  the application code, so review its cost before provisioning it. If used,
  keep it private and allow access only from the backend.

The retrieval integration test requires `vector` to be installed in its test
database. AWS RDS permissions and supported extension versions differ from a
local pgvector container, so validate the migration against the chosen RDS
engine before production rollout.

### Frontend

For the normal static frontend deployment, use AWS Amplify Hosting or Vercel
connected to the repository. Set the project/root directory to `frontend/`,
install from `package-lock.json` with `npm ci`, and build with `npm run build`.
Publish the generated `frontend/dist/` directory. Add a single-page-app
fallback/rewrite to `index.html` so React Router routes such as `/chat` and
`/staff` load on refresh.

The repository also contains `frontend/Dockerfile` and `frontend/nginx.conf`
for a containerized Nginx frontend. These are useful if the frontend is served
as a container; Amplify/Vercel do not use that Dockerfile.

#### Required frontend/API integration before production

The current frontend API client in `frontend/src/lib/api.ts` uses the literal
base URL `http://localhost:8000`. That is for local development and will
attempt to call the visitor's own computer in a deployed site. Before a
production frontend build, make the API base configurable (for example via
`import.meta.env.VITE_API_BASE_URL`) and set it to the public HTTPS API origin,
or change the client to call a same-origin `/api` prefix and route that prefix
through a reverse proxy.

The current API endpoints are rooted at `/login`, `/chat`, `/appointments`,
and so on. The supplied Nginx configuration proxies `/api/` and strips that
prefix, so a same-origin deployment must make the frontend use `/api` as its
base URL. The `VITE_API_BASE_URL` environment entry in the production Compose
file is not read by the current API client and is not sufficient by itself.

The backend currently allows CORS only from `http://localhost:5173`. Before
using a separate Amplify/Vercel domain, make allowed origins configurable and
allow only the production frontend origin(s) over HTTPS. Do not use wildcard
origins for an authenticated application.

## CI/CD: build and push to ECR

### One-time AWS setup

1. Choose one AWS region and create private ECR repositories, for example
   `doctorly-api` and `doctorly-frontend`. Enable image scanning and lifecycle
   policies so old untagged images are cleaned up.
2. Configure GitHub Actions OpenID Connect (OIDC) as an identity provider in
   AWS IAM. Create a dedicated deploy role whose trust policy is limited to
   this GitHub organization/repository and the intended branch or GitHub
   environment. Avoid long-lived AWS access keys in GitHub secrets.
3. Give the role only the required ECR permissions (authenticate and upload
   image layers / image manifests for these repositories). Add separate
   permissions for updating the chosen compute service only if the workflow
   will deploy it.
4. Configure GitHub repository variables for non-secret identifiers such as
   `AWS_REGION`, `AWS_ACCOUNT_ID`, ECR repository names, and the role ARN.
   Configure production secrets in AWS Secrets Manager or Systems Manager
   Parameter Store, not in Git or a checked-in environment file.
5. Add a release workflow (or extend the current workflow) that checks out the
   source, assumes the IAM role with GitHub OIDC, logs in to ECR, and uses
   `docker/build-push-action` to build and push both images. Tag images with
   the commit SHA and optionally a release version; deploy an immutable SHA
   tag rather than relying only on `latest`.

The existing `.github/workflows/ci.yml` builds the **backend** image with
`push: false` to verify its Dockerfile. It does not publish an image. The
workflow's frontend job validates the React app but does not build/push the
frontend Docker image.

### Build context and architectures

- Backend: build with repository root as the context and `Dockerfile` as the
  file. The image is Python 3.12 and runs Uvicorn as the unprivileged
  `appuser`.
- Frontend container: build with `frontend/` as the context and
  `frontend/Dockerfile` as the file. It serves the static build with Nginx.
- If deploying to ARM-based compute, explicitly set the build platform to
  match the service architecture or publish a multi-platform manifest.
- Use ECR image scanning and review findings before promotion.

## Runtime configuration and secrets

Configure these values in the managed compute service. Do not put secret
values in image build arguments, Dockerfiles, source control, or GitHub Actions
logs.

| Setting | Purpose |
|---|---|
| `DOCTORLY_DATABASE_URL` | SQLAlchemy URL to the private RDS instance, using the `postgresql+psycopg` driver |
| `DOCTORLY_JWT_SECRET_KEY` | Unique random signing secret; at least 32 bytes |
| `LLM_PROVIDER`, `LLM_MODEL` | Model provider and model identifier; current default is Google / `gemini-1.5-flash` |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Gemini credential, if Google is selected |
| `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_ENDPOINT` | Optional tracing configuration |
| `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Optional OpenTelemetry service name and OTLP export endpoint |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `EMAIL_FROM` | Optional appointment email delivery configuration |
| `LOG_LEVEL` | Structured application logging level |

Use the platform's task/service IAM role to retrieve secrets at runtime, or
inject secrets using its managed secret integration. Rotate credentials and
signing keys using a planned rollout; changing a JWT signing secret invalidates
existing access tokens. Encode reserved characters in database URLs or use a
secret/connection mechanism that avoids URL parsing ambiguity.

LangSmith traces may include patient messages and model inputs/outputs.
Tracing is disabled by default. Do not enable tracing with real patient
information unless privacy, retention, access, and contractual requirements
have been reviewed and the data handling is explicitly approved. The
application's JSON log redaction does not sanitize LangSmith traces.

Email is currently triggered as an in-process asynchronous task after booking.
This is best-effort: a process restart can interrupt delivery. Before
appointments depend on guaranteed email, use a durable queue/outbox and a
worker (for example, SQS plus a worker or a transactional outbox), and consider
Amazon SES rather than embedding SMTP credentials in the application.

## Database migrations and release order

Use a migration step that can reach RDS privately, such as a one-off ECS/Fargate
task launched in the same VPC with the same backend image and a command of
`alembic upgrade head`. Do not run migrations independently from every
application replica at startup.

Recommended release sequence:

1. Build, scan, and push immutable backend/frontend image tags.
2. Run the migration task and require it to succeed.
3. Deploy the backend image and wait for health checks.
4. Deploy the frontend with its production API base and route fallback.
5. Smoke-test `/health`, `/health/ready`, sign-in, patient booking, and staff
   authorization using non-production test identities.
6. Monitor error rates, database connections, latency, and costs; retain the
   previous image tag for rollback.

Migrations should be backward-compatible across a rolling deploy: add nullable
or additive schema first, deploy code that uses it, and remove old schema only
in a later release.

## Production hardening checklist

- [ ] Select the AWS region and estimate steady-state plus peak cost before
  provisioning RDS, ElastiCache, load balancers, and always-on compute.
- [ ] Use private subnets for RDS and Redis; restrict security groups to
  backend sources and required ports.
- [ ] Enable encryption, backups, retention, deletion protection, and alerts
  for database storage.
- [ ] Keep API and frontend on HTTPS with managed certificates and custom
  domains.
- [ ] Configure production CORS and the frontend API base as described above.
- [ ] Use GitHub OIDC and least-privilege IAM; do not use long-lived AWS keys.
- [ ] Store runtime secrets in AWS-managed secret storage and rotate them.
- [ ] Decide whether LangSmith tracing is appropriate for the data processed.
- [ ] Provision staff accounts through a trusted administrative process;
  public registration is patient-only.
- [ ] Validate RDS pgvector migrations and backups/restores before real use.
- [ ] Add monitoring, log retention, incident procedures, and a rollback plan.
- [ ] Do not use real patient information until security, privacy, regulatory,
  and operational reviews are complete.

## Production Compose file

`docker-compose.prod.yml` is a Compose deployment template that expects its
required secret variables from an external `.env.prod` or environment. It
does not provision AWS managed RDS/ElastiCache or replace the managed-service
architecture above. It also exposes the API and Nginx frontend ports for
container-host use while leaving PostgreSQL un-published. Do not treat it as an
AWS service deployment specification.

## AWS references

- [AWS App Runner availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)
- [Amazon ECS Express Mode getting started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html)
- [GitHub Actions: configuring OpenID Connect in AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [Amazon RDS for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Amazon ECR user guide](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
