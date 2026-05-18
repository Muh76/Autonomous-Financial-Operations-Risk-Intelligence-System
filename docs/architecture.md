# Backend Architecture

## Project Structure

```text
.
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── v1/
│   │       └── routes/
│   ├── core/
│   │   └── graph/
│   ├── db/
│   ├── integrations/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── tasks/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Responsibilities

- `app/main.py`: FastAPI application factory and router registration.
- `app/api`: HTTP routing boundary, dependency aliases, and exception handlers.
- `app/api/routes`: Non-versioned platform routes such as `/health`.
- `app/api/v1/router.py`: Aggregates all versioned API modules under `/api/v1`.
- `app/api/v1/routes`: Versioned endpoint modules.
- `app/core/config.py`: Pydantic settings loaded from environment variables.
- `app/core/logging.py`: Structured logging configuration.
- `app/core/lifespan.py`: Startup and shutdown lifecycle hooks.
- `app/core/middleware.py`: Request middleware registration, currently request ID propagation.
- `app/core/graph`: Typed LangGraph state and workflow definition.
- `app/db/session.py`: Async SQLAlchemy engine and session dependency.
- `app/models`: SQLAlchemy models.
- `app/repositories`: Persistence adapters.
- `app/schemas`: Pydantic request, response, and error contracts.
- `app/services`: Application use cases separated from HTTP transport.
- `app/integrations`: External system clients.
- `app/tasks`: Background and scheduled jobs.

## Architecture

The backend follows a small layered structure:

```text
FastAPI routes -> dependencies -> services -> graph/repositories/integrations -> PostgreSQL/Redis/external systems
```

Routes stay thin: they validate input, resolve dependencies, call services, and return typed response envelopes. Services own application behavior. Repositories will own persistence. Integrations will own external system calls. LangGraph workflows live under `core/graph` until domain-specific agent packages are justified.

Current routes:

- `GET /health`
- `GET /api/v1/patients`
- `POST /api/v1/patients`
- `POST /api/v1/safety`
- `POST /api/v1/evaluation`

## Why Routing Structure Matters

Non-versioned routes are reserved for platform concerns that should not change with business API versions, such as health checks. Domain routes sit under `/api/v1` so future breaking changes can be introduced as `/api/v2` without disturbing existing clients.

Each domain has its own route module. This keeps patient, safety, and evaluation concerns independent while still giving the application one top-level router to register.

## Infrastructure

Docker Compose starts:

- `api`: FastAPI application served by Uvicorn.
- `postgres`: PostgreSQL for durable platform data.
- `redis`: Redis for cache, locks, rate limits, and transient workflow state.

## Service Flow

```text
Client -> FastAPI route -> typed Python boundary -> async service/workflow -> response
```

## Scaling Toward AI Agents

This structure scales cleanly for AI agent workflows because agents do not need to leak into route code. A future route can call a service, the service can invoke a LangGraph workflow, and graph nodes can use repositories or integrations through explicit interfaces.

As the platform grows:

- patient routes can remain focused on patient-facing API operations
- safety routes can call deterministic policy services and graph-based risk workflows
- evaluation routes can run offline or online AI quality checks
- agent state can stay typed in `core/graph/state.py`
- long-running workflows can move into `tasks`

The result is an API that can support AI orchestration without becoming an API-shaped prompt runner.
