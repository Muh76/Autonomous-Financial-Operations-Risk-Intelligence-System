# Autonomous Financial Operations & Risk Intelligence Platform

Backend foundation for an enterprise AI system that supports financial operations review, transaction investigation, safety checks, and evaluation workflows.

The current codebase is an initial production-style backend scaffold. It focuses on clean service boundaries, async infrastructure, typed workflow state, health reporting, and local operability. Domain models and production business rules are intentionally minimal at this stage.

## Project Vision

The platform is intended to become a backend system for autonomous and human-supervised financial operations intelligence. Its long-term purpose is to help teams inspect transactions, identify operational and risk signals, coordinate investigation workflows, and maintain auditable decision trails.

Core engineering goals:

- provide a reliable async API layer for operational workflows
- support future multi-agent investigation and risk workflows
- persist operational data and audit records in PostgreSQL
- use Redis for cache, transient workflow state, and investigation memory
- expose production-grade health and structured logging from the start
- keep domain logic separated from transport, persistence, and orchestration concerns

## Architecture Overview

The backend follows a layered architecture:

```text
Client
  -> FastAPI routes
  -> dependency injection
  -> service layer
  -> LangGraph workflows / repositories / integrations
  -> PostgreSQL / Redis / external systems
```

Current architecture components:

- FastAPI app factory with lifespan startup and shutdown handlers
- versioned API routing under `/api/v1`
- non-versioned platform health endpoint at `/health`
- centralized Pydantic settings
- structured logging with request context binding
- async SQLAlchemy database integration
- async Redis integration
- typed LangGraph investigation workflow
- PostgreSQL workflow persistence models and investigation repository
- Redis workflow state cache and resume pointer helpers
- Docker Compose for local API, PostgreSQL, and Redis

## Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic Settings
- SQLAlchemy asyncio
- asyncpg
- PostgreSQL
- Redis asyncio client
- LangGraph
- LangChain
- Structlog
- Docker Compose

## Folder Structure

```text
app/
|-- api/
|   |-- routes/          # non-versioned platform routes such as /health
|   |-- v1/              # versioned API router and domain endpoints
|   |-- dependencies.py  # FastAPI dependency aliases
|   |-- errors.py        # centralized exception handlers
|   `-- router.py        # top-level API router registration
|-- cache/               # Redis client, healthcheck, cache/state helpers
|-- core/
|   |-- graph/           # LangGraph state schemas, nodes, and workflow assembly
|   |-- config.py        # environment-driven settings
|   |-- health.py        # dependency healthcheck orchestration
|   |-- lifespan.py      # startup/shutdown lifecycle
|   |-- logging.py       # structlog configuration and logger utility
|   `-- middleware.py    # request tracing middleware
|-- db/                  # async SQLAlchemy engine and session management
|-- integrations/        # future external systems and vendor clients
|-- models/              # SQLAlchemy ORM models
|-- repositories/        # persistence boundaries and repositories
|-- schemas/             # Pydantic request and response models
|-- services/            # application service layer
`-- tasks/               # future background jobs and scheduled workflows
```

Additional project files:

```text
examples/                # runnable examples for workflow, Redis, and logging
docs/                    # architecture notes
Dockerfile               # backend container image
docker-compose.yml       # local API/PostgreSQL/Redis stack
requirements.txt         # minimal direct runtime dependencies
.env.example             # local environment template
```

## Local Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the API docs:

```text
http://localhost:8000/docs
```

## Docker Usage

Start the full local stack:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- `aforis-api`: FastAPI backend on port `8000`
- `aforis-postgres`: PostgreSQL database
- `aforis-redis`: Redis cache/state store

Stop the stack:

```bash
docker compose down
```

Remove local volumes when a clean database/cache is needed:

```bash
docker compose down -v
```

## API Routes

```text
GET  /health
GET  /api/v1/patients
POST /api/v1/patients
POST /api/v1/safety
POST /api/v1/evaluation
```

## Healthcheck System

The `/health` endpoint returns an enterprise-style component response.

It validates:

- FastAPI application readiness
- PostgreSQL connectivity
- Redis connectivity
- LangGraph workflow initialization

Example shape:

```json
{
  "success": true,
  "request_id": "request-id",
  "status": "degraded",
  "environment": "local",
  "version": "0.1.0",
  "components": {
    "app": {
      "status": "ok",
      "latency_ms": 0.01,
      "detail": "FastAPI application is ready"
    }
  }
}
```

When PostgreSQL or Redis are unavailable in local development, the endpoint reports `degraded` instead of crashing.

## Workflow Overview

The LangGraph workflow is a financial investigation workflow located in `app/core/graph`.

Current workflow capabilities:

- modular typed investigation state with evidence, findings, risk, approvals, errors, and history
- nested schemas for transaction context, compliance reviews, risk assessments, persistent memory, node results, and agent executions
- async-ready nodes for transaction context, fraud, compliance, risk, critic, escalation, and reporting
- deterministic conditional routing for low-risk auto-close, medium-risk compliance review, high-risk escalation, evidence expansion, and failure
- reusable retry manager with failure classification, retry exhaustion tracking, and deterministic fallback hooks
- approval checkpoint state for future human-in-the-loop review
- optional checkpointer injection for durable LangGraph persistence

State schema modules:

```text
app/core/graph/state.py                    # canonical LangGraph state contract
app/core/graph/state_schemas/enums.py      # statuses, routes, risk bands, agent roles
app/core/graph/state_schemas/evidence.py   # evidence references and investigation findings
app/core/graph/state_schemas/history.py    # workflow events, approvals, escalations
app/core/graph/state_schemas/execution.py  # node results, retries, confidence, agent runs
app/core/graph/state_schemas/risk.py       # risk assessment contract
app/core/graph/state_schemas/investigation.py # transaction, subject, compliance, memory
app/core/graph/retry.py                    # retry manager, policies, fallback utilities
app/models/investigations.py               # workflow run, snapshot, history, checkpoint models
app/repositories/investigations.py         # investigation persistence repository
```

Run the workflow example:

```bash
python examples/run_investigation_workflow.py
```

The workflow uses typed state and reducer-based list updates so future nodes and agents can append evidence, findings, errors, approvals, escalations, node results, agent executions, and history without overwriting prior state.

See `docs/langgraph_investigation_workflow.md` for the architecture map and production guidance.
See `docs/workflow_persistence_architecture.md` for the persistence, checkpointing, Redis, and PostgreSQL design.

## Logging and Observability

Structured logging is configured with `structlog`.

Current support:

- JSON logs in production-style environments
- readable console logs for local development
- request ID propagation through `X-Request-ID`
- request context binding for method, path, and client host
- request start, completion, failure, and duration logs

Run the logging example:

```bash
python examples/logging_usage.py
```

This structure is ready for future OpenTelemetry, centralized log ingestion, and trace correlation.

## Redis Usage

Redis is integrated through `app/cache/redis.py`.

Current support:

- async connection pool
- FastAPI dependency injection
- healthcheck helper
- JSON cache helper
- workflow history helper
- workflow state cache helper
- workflow resume pointer helper
- short-lived execution event stream helper

Run the Redis example after starting Redis:

```bash
python examples/redis_usage.py
```

## Roadmap

Near-term backend work:

- add Alembic migrations for investigation persistence models
- implement repository interfaces for patients, transactions, investigations, and evaluations
- connect services to PostgreSQL persistence
- add test suite with async database and Redis fixtures
- add CI checks for formatting, typing, tests, and container build

AI workflow work:

- connect investigation workflow nodes to real fraud, compliance, and risk services
- add LangGraph interrupt/resume support for human approval checkpoints
- persist workflow runs and decision trails
- introduce agent/tool interfaces for external data retrieval

Operational work:

- add OpenTelemetry tracing
- add metrics endpoint
- add authentication and authorization
- add rate limiting and idempotency keys
- add production deployment manifests

## Future Phases

Phase 1: Backend Foundation

- API structure
- configuration
- healthchecks
- logging
- PostgreSQL and Redis connectivity
- minimal LangGraph workflow

Phase 2: Domain Persistence

- transaction, patient, investigation, and evaluation models
- migrations
- repositories
- audit records

Phase 3: Risk Intelligence Workflows

- richer LangGraph workflows
- deterministic policy checks
- risk scoring services
- workflow state persistence
- investigation memory

Phase 4: Multi-Agent Operations

- specialized investigation agents
- safety and evaluation agents
- tool calling interfaces
- human-in-the-loop escalation
- traceable agent decisions

Phase 5: Production Operations

- authentication and tenant isolation
- observability dashboards
- deployment automation
- security hardening
- performance and resilience testing

## Current Status

This repository is an early backend foundation. It is structured to support production growth, but the domain behavior is intentionally minimal until financial operation requirements, data contracts, and governance rules are defined.
