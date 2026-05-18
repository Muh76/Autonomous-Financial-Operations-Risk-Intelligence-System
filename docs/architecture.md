# Backend Architecture

## 1. Recommended Folder Structure

```text
.
├── app/
│   ├── api/                 # FastAPI routers and versioned HTTP endpoints
│   ├── agents/              # LangGraph state, graphs, and future agent nodes
│   ├── cache/               # Redis clients, cache helpers, distributed locks
│   ├── core/                # Settings, logging, security, common app primitives
│   ├── db/                  # SQLAlchemy engine/session and database lifecycle
│   ├── integrations/        # External financial systems and third-party clients
│   ├── models/              # ORM models
│   ├── observability/       # Health checks, metrics, tracing, audit hooks
│   ├── repositories/        # Persistence adapters and query boundaries
│   ├── schemas/             # Pydantic request/response contracts
│   ├── services/            # Business use cases and orchestration boundaries
│   └── tasks/               # Background jobs and scheduled workflows
├── docs/                    # Architecture and operating notes
├── docker-compose.yml       # Local API, PostgreSQL, Redis stack
├── Dockerfile               # API image
├── pyproject.toml           # Python dependencies and tooling config
└── .env.example             # Local environment template
```

## 2. Folder Responsibilities

- `app/api`: HTTP boundary only. It validates requests, calls services, and returns response schemas.
- `app/services`: Application use cases. This is where endpoint intent becomes business behavior.
- `app/agents`: LangGraph orchestration. Keep graph state typed and node functions small.
- `app/schemas`: Pydantic API contracts. These should be stable and explicit.
- `app/models`: SQLAlchemy persistence models.
- `app/repositories`: Database access layer. Services depend on repositories instead of raw queries.
- `app/db`: Async database engine/session setup and future migration hooks.
- `app/cache`: Redis connection and future cache/state abstractions.
- `app/integrations`: Clients for ERP, banking, payment, KYC, market data, notification, and document systems.
- `app/core`: Cross-cutting configuration, logging, security, and app-level dependencies.
- `app/observability`: Health, metrics, tracing, structured logging, and audit-ready instrumentation.
- `app/tasks`: Background processing entrypoints for long-running analysis, reconciliation, and alerting.

## 3. Recommended Backend Architecture

Use a layered backend:

```text
HTTP API -> Services -> Agents / Repositories / Integrations -> PostgreSQL / Redis / External Systems
```

The FastAPI layer should stay thin. Services own use-case orchestration, such as analyzing an operation, assessing counterparty exposure, or triggering a review workflow. LangGraph should coordinate multi-step reasoning and decision workflows while keeping deterministic business rules in normal Python services.

State should be typed at graph boundaries. The scaffold uses `FinancialOperationState` as a `TypedDict`, which can later evolve into stricter Pydantic state objects if persistence, validation, or schema versioning becomes necessary.

For future multi-agent support, keep each graph node focused on one responsibility:

- context enrichment
- risk classification
- policy validation
- anomaly detection
- recommendation generation
- human approval routing

Avoid turning agents into repositories or API clients. Agent nodes may call tools, but persistence and external integration should still sit behind service/repository/client interfaces.

## 4. Infrastructure Overview

Local infrastructure runs through Docker Compose:

- `api`: FastAPI application served by Uvicorn.
- `postgres`: durable relational store for operations, assessments, audit records, graph checkpoints, and configuration.
- `redis`: cache, transient workflow state, idempotency keys, rate limits, and lightweight distributed locks.

Production can map this cleanly to:

- containerized API services behind a load balancer
- managed PostgreSQL with backups and read replicas where needed
- managed Redis with persistence configured according to workflow needs
- OpenTelemetry collector for traces and metrics
- centralized structured log ingestion
- secret manager for credentials

## 5. Service Interaction Flow

Example operation analysis flow:

```text
Client
  -> POST /api/v1/operations/analyze
  -> FastAPI route validates OperationRequest
  -> OperationsService creates typed graph state
  -> LangGraph enrich_context node prepares context
  -> LangGraph assess_risk node classifies initial risk
  -> LangGraph recommend_actions node prepares next actions
  -> Service maps graph result to OperationResponse
  -> Client receives risk level, findings, and recommendations
```

In a fuller production version, the service would also:

- load account, transaction, policy, and counterparty data through repositories and integrations
- cache repeated reference data in Redis
- persist the workflow request, decision trail, and audit events in PostgreSQL
- emit trace spans and structured logs around each graph node
- enqueue long-running or human-in-the-loop workflows through `app/tasks`

The current implementation is intentionally minimal: it establishes the architecture, async boundaries, typed state, and service flow without pretending the domain model is complete.
