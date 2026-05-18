# Autonomous Financial Operations & Risk Intelligence Platform

Production-style backend scaffold for an AI-assisted financial operations and risk intelligence platform.

## Stack

- FastAPI for the HTTP API
- LangGraph for workflow and future multi-agent orchestration
- PostgreSQL for durable persistence
- Redis for cache, locks, and transient state
- Docker Compose for local infrastructure
- Pydantic settings and typed graph state

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

API health check:

```bash
curl http://localhost:8000/api/v1/health
```

See [docs/architecture.md](docs/architecture.md) for the architecture, folder responsibilities, infrastructure overview, and service flow.
