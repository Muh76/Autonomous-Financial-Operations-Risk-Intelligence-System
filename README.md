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
- production-style parallel LangGraph workflow example
- PostgreSQL workflow persistence models and investigation repository
- PostgreSQL durable workflow memory models and repository
- Redis workflow state, resume pointer, execution event, and short-term memory helpers
- workflow memory service for agent context assembly
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
- fan-out/fan-in parallel execution example for fraud analysis and compliance validation
- deterministic conditional routing for low-risk auto-close, medium-risk compliance review, high-risk escalation, evidence expansion, and failure
- reusable retry manager with failure classification, retry exhaustion tracking, and deterministic fallback hooks
- timeout fallback handling for parallel async branches
- result aggregation after parallel branch completion
- human approval checkpoint architecture for high-risk escalation pause/resume
- workflow visualization metadata for dashboards, timelines, and replay systems
- production-style pytest architecture for deterministic LangGraph workflow validation
- production-grade Transaction Analysis Agent for aggregation, temporal analysis, anomaly heuristics, and chain analysis
- explainable Fraud Detection Agent with deterministic heuristics and AI-assisted narrative support
- Financial Retrieval Agent with RAG, reranking, citations, and grounded evidence
- Risk Scoring Agent for weighted operational risk, confidence calibration, and escalation prioritization
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
app/core/graph/parallel_workflow.py        # parallel fan-out/fan-in workflow example
app/core/graph/transaction_analysis_node.py # Transaction Analysis Agent node wrapper
app/core/graph/fraud_detection_node.py     # Fraud Detection Agent node wrapper
app/core/graph/financial_retrieval_node.py # Financial Retrieval Agent node wrapper
app/core/graph/risk_scoring_agent_node.py  # Risk Scoring Agent node wrapper
app/models/investigations.py               # workflow run, snapshot, history, checkpoint models
app/repositories/investigations.py         # investigation persistence repository
app/models/memory.py                       # durable workflow memory, evidence, retry, feedback models
app/repositories/memory.py                 # workflow memory repository
app/services/workflow_memory.py            # Redis/PostgreSQL agent memory service
app/services/approval_checkpoints.py       # approval decision and pause/resume helpers
app/services/workflow_visualization.py     # dashboard and replay metadata builder
app/services/transaction_analysis.py       # deterministic transaction analysis agent service
app/services/fraud_detection.py            # explainable fraud scoring and evidence service
app/services/financial_retrieval.py        # RAG retrieval, reranking, citation, grounding service
app/services/risk_scoring.py               # weighted operational risk scoring service
```

Run the workflow example:

```bash
python examples/run_investigation_workflow.py
```

Run the parallel workflow example:

```bash
python examples/run_parallel_investigation_workflow.py
```

The workflow uses typed state and reducer-based list updates so future nodes and agents can append evidence, findings, errors, approvals, escalations, node results, agent executions, and history without overwriting prior state.

See `docs/langgraph_investigation_workflow.md` for the architecture map and production guidance.
See `docs/workflow_persistence_architecture.md` for the persistence, checkpointing, Redis, and PostgreSQL design.
See `docs/workflow_memory_architecture.md` for the workflow memory architecture, Redis short-term memory, PostgreSQL durable memory, and repository strategy.
See `docs/parallel_execution_architecture.md` for scalable parallel execution, async node patterns, aggregation, and timeout handling.
See `docs/human_approval_checkpoint_architecture.md` for high-risk escalation checkpoints, approval states, audit logging, and pause/resume strategy.
See `docs/workflow_visualization_metadata.md` for graph metadata, node timing, edge traversal, retry visualization, and timeline generation.
See `docs/workflow_testing_architecture.md` for pytest structure, fixtures, node isolation tests, branching tests, retry tests, and workflow integration tests.
See `docs/transaction_analysis_agent.md` for the Transaction Analysis Agent architecture, typed outputs, pipeline, and LangGraph node wrapper.
See `docs/fraud_detection_agent.md` for explainable fraud scoring, evidence generation, heuristics, typed outputs, and LangGraph integration.
See `docs/financial_retrieval_agent.md` for RAG architecture, ingestion, vector retrieval, reranking, citations, grounding, and LangGraph integration.
See `docs/risk_scoring_agent.md` for weighted scoring, confidence calibration, escalation recommendations, typed outputs, and LangGraph integration.

## Workflow Memory

The workflow memory layer supports long-running multi-agent investigations with both short-term and durable memory.

Redis is used for:

- active workflow memory
- agent scratchpads
- agent handoffs
- retry counters
- latest critic feedback

PostgreSQL is used for:

- investigation and workflow summaries
- related transaction memory
- evidence history
- prior escalations
- retry history
- critic feedback history

Agents should access memory through `WorkflowMemoryService` instead of directly reading Redis or PostgreSQL. This keeps memory retrieval tenant-scoped, auditable, and easier to evolve as agent workflows become more complex.

## Parallel Execution

The parallel workflow demonstrates production-style AI orchestration where fraud analysis and compliance validation execute concurrently, then join at a deterministic aggregation node.

Concurrency safety is handled by:

- assigning disjoint scalar fields to each parallel branch
- using reducer-backed append-only lists for shared history and observations
- centralizing aggregate risk decisions in the join node
- wrapping branch execution with timeout fallbacks
- recording branch outputs, errors, and agent execution metadata

## Workflow Visualization

The visualization metadata layer turns LangGraph execution state into dashboard-ready read models.

It supports:

- static graph node and edge metadata
- node execution timing
- edge traversal tracking
- retry visualization
- escalation path tracking
- workflow timeline generation

`WorkflowVisualizationService` builds visualization payloads from workflow state, including existing `workflow_history`, `node_results`, `agent_executions`, `retry_state`, and `escalations`. This keeps dashboards and replay systems rebuildable from durable workflow history.

## Workflow Testing

The test scaffold is organized around deterministic LangGraph validation.

Current test layers:

- node isolation tests
- branching and state transition tests
- retry policy tests
- approval checkpoint tests
- visualization metadata tests
- workflow integration tests

Run the test suite:

```bash
pytest tests
```

Run only fast unit coverage:

```bash
pytest tests/unit
```

The tests use complete mock `InvestigationState` fixtures and avoid external services, so they are suitable for CI expansion as the workflow grows.

## Transaction Analysis Agent

The Transaction Analysis Agent provides deterministic transaction intelligence for financial investigations.

It supports:

- transaction aggregation
- temporal velocity and burst analysis
- behavioral pattern detection
- anomaly heuristics
- transaction chain analysis
- suspicious activity indicators
- confidence scoring
- LangGraph-compatible state updates

Run the example:

```bash
python examples/run_transaction_analysis_agent.py
```

The agent emits a typed `TransactionAnalysisResult` and maps it into workflow state as `transaction_analysis`, `fraud_score`, `fraud_typologies`, evidence, findings, and agent execution metadata.

## Fraud Detection Agent

The Fraud Detection Agent provides explainable fraud scoring for enterprise investigations.

It supports:

- anomaly scoring
- suspicious behavior analysis
- geographic inconsistency checks
- transaction velocity checks
- fraud heuristic evidence generation
- escalation recommendations
- deterministic scoring with AI-assisted narrative extension points

Run the example:

```bash
python examples/run_fraud_detection_agent.py
```

The agent emits a typed `FraudDetectionResult` and maps it into workflow state as `fraud_detection`, `fraud_score`, `risk_band`, `fraud_typologies`, evidence, findings, recommended actions, and agent execution metadata.

## Financial Retrieval Agent

The Financial Retrieval Agent provides trustworthy RAG for investigation evidence grounding.

It supports:

- semantic retrieval
- deterministic embedding fallback
- reranking
- citation generation
- evidence grounding
- compliance document retrieval
- source attribution
- confidence scoring

Supported document families include SEC filings, audit reports, compliance policies, AML guidance, and governance reports.

Run the example:

```bash
python examples/run_financial_retrieval_agent.py
```

The agent emits a typed `FinancialRetrievalResponse` and maps grounded retrieval output into workflow evidence, findings, citations, and agent execution metadata.

## Risk Scoring Agent

The Risk Scoring Agent aggregates investigation signals into explainable operational risk.

It uses weighted inputs from:

- fraud signals
- compliance violations
- transaction anomaly scores
- retrieval evidence and citations
- critic feedback
- operational context

Run the example:

```bash
python examples/run_risk_scoring_agent.py
```

The agent emits a typed `OperationalRiskScore` and maps it into workflow state as `operational_risk`, `risk_assessment`, `aggregate_risk_score`, `risk_band`, `escalation_level`, findings, recommended actions, and agent execution metadata.

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
- active workflow memory helper
- agent scratchpad helper
- agent handoff helper
- retry counter helper
- latest critic feedback helper

Run the Redis example after starting Redis:

```bash
python examples/redis_usage.py
```

## Roadmap

Near-term backend work:

- add Alembic migrations for workflow memory models
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
- wire workflow memory service into graph node execution boundaries
- add critic review routing after low-confidence parallel branch fallbacks
- expose workflow visualization metadata through API endpoints
- expand workflow tests with repository, Redis, and checkpointer integration coverage
- integrate the Transaction Analysis Agent into the default investigation graph
- integrate the Fraud Detection Agent into the default investigation graph
- integrate the Financial Retrieval Agent before critic review and final report generation
- integrate the Risk Scoring Agent as the default risk scoring node

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
- parallel fraud/compliance branch orchestration

Phase 4: Multi-Agent Operations

- specialized investigation agents
- safety and evaluation agents
- tool calling interfaces
- human-in-the-loop escalation
- traceable agent decisions
- durable memory retrieval and feedback loops

Phase 5: Production Operations

- authentication and tenant isolation
- observability dashboards
- deployment automation
- security hardening
- performance and resilience testing

## Current Status

This repository is an early backend foundation. It is structured to support production growth, but the domain behavior is intentionally minimal until financial operation requirements, data contracts, and governance rules are defined.
