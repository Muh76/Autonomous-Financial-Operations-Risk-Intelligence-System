# Autonomous Financial Operations & Risk Intelligence Platform

Production-style backend starter for an AI-assisted financial operations and risk intelligence platform.

The project currently includes an async FastAPI API, Docker Compose infrastructure, PostgreSQL and Redis wiring, structured logging, typed settings, and a minimal LangGraph financial investigation workflow.

## Stack

- FastAPI for the async HTTP API
- LangGraph and LangChain for workflow orchestration and future AI agents
- PostgreSQL with async SQLAlchemy and `asyncpg`
- Redis for cache, locks, and transient workflow state
- Docker Compose for local development infrastructure
- Pydantic Settings for centralized configuration
- Structlog for structured JSON logging

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

API health check:

```bash
curl http://localhost:8000/health
```

Interactive API docs are available locally at:

```text
http://localhost:8000/docs
```

## Current API Routes

```text
GET  /health
GET  /api/v1/patients
POST /api/v1/patients
POST /api/v1/safety
POST /api/v1/evaluation
```

## LangGraph Investigation Workflow

The starter workflow lives in `app/core/graph` and uses a typed investigation state with reducer-based list updates for scalable future agent nodes.

State fields:

- `transaction_id`
- `findings`
- `risk_score`
- `escalation_level`
- `workflow_history`

Run the example:

```bash
python examples/run_investigation_workflow.py
```

## Project Layout

```text
app/
├── api/              # route registration, dependency aliases, error handling
├── core/             # config, logging, middleware, lifespan, graph workflow
├── db/               # async SQLAlchemy session setup
├── integrations/     # external system clients
├── models/           # ORM models
├── repositories/     # persistence boundaries
├── schemas/          # Pydantic request and response models
├── services/         # application service layer
└── tasks/            # background and scheduled jobs
```

## Local Development

Install dependencies without Docker:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docker services:

- `aforis-api`
- `aforis-postgres`
- `aforis-redis`

See [docs/architecture.md](docs/architecture.md) for folder responsibilities, routing structure, infrastructure overview, and how the backend scales toward multi-agent workflows.
