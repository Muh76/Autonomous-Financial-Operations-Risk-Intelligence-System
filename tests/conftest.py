from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest

from app.core.graph.state import InvestigationState
from app.core.graph.workflow import SCHEMA_VERSION, WORKFLOW_VERSION


StateFactory = Callable[..., InvestigationState]


@pytest.fixture
def investigation_state_factory() -> StateFactory:
    def build(**overrides: Any) -> InvestigationState:
        state: InvestigationState = {
            "case_id": "case_test_txn",
            "tenant_id": "test_tenant",
            "thread_id": "thread_test_tenant_test_txn",
            "transaction_id": "test_txn",
            "workflow_version": WORKFLOW_VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "initialized",
            "transaction_amount": 125.0,
            "transaction_currency": "USD",
            "jurisdiction": "US",
            "evidence": [],
            "findings": [],
            "workflow_history": [],
            "node_errors": [],
            "approvals": [],
            "escalations": [],
            "node_results": [],
            "agent_executions": [],
            "node_traces": [],
            "edge_traversals": [],
            "timeline_events": [],
            "retry_counts": {},
            "retry_state": {},
            "fallback_used": {},
        }
        state.update(overrides)
        return deepcopy(state)

    return build


@pytest.fixture
def low_risk_state(investigation_state_factory: StateFactory) -> InvestigationState:
    return investigation_state_factory(transaction_amount=125.0, jurisdiction="US")


@pytest.fixture
def high_risk_state(investigation_state_factory: StateFactory) -> InvestigationState:
    return investigation_state_factory(transaction_amount=75_000.0, jurisdiction="US")


@pytest.fixture
def sanctions_state(investigation_state_factory: StateFactory) -> InvestigationState:
    return investigation_state_factory(transaction_amount=2_500.0, jurisdiction="IR")
