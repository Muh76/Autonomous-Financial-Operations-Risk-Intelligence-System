from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from app.core.graph.state import (
    FailureClass,
    InvestigationState,
    NodeError,
    NodeExecutionStatus,
    NodeResult,
    RetryState,
    WorkflowEvent,
    WorkflowEventStatus,
)


PartialState = dict[str, Any]
NodeHandler = Callable[[InvestigationState], Awaitable[PartialState]]
FallbackName = Literal["deterministic_fallback", "manual_review", "skip_optional_node"]


class NonRecoverableNodeError(RuntimeError):
    """Raise when a node failure should bypass retries and go directly to failure routing."""


class RecoverableNodeError(RuntimeError):
    """Raise when a node failure is expected to recover through retry or fallback routing."""


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for a workflow node."""

    max_attempts: int = 2
    retry_route: str = "evidence_expansion"
    failure_route: str = "workflow_failure"
    recoverable_failure_classes: tuple[FailureClass, ...] = (
        "transient",
        "rate_limit",
        "timeout",
        "dependency",
        "semantic",
        "unknown",
    )
    fallback_name: FallbackName | None = None


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(node: str, status: WorkflowEventStatus, message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": node,
        "status": status,
        "message": message,
        "created_at": _now(),
    }


def _node_result(
    node: str,
    status: NodeExecutionStatus,
    output_fields: list[str],
    *,
    next_route: str | None = None,
    error: NodeError | None = None,
) -> NodeResult:
    result: NodeResult = {
        "node": node,
        "status": status,
        "created_at": _now(),
        "output_fields": output_fields,
    }
    if next_route is not None:
        result["next_route"] = next_route
    if error is not None:
        result["error"] = error
    return result


class ErrorClassifier:
    """Classify node exceptions into workflow-relevant failure classes."""

    def classify(self, error: Exception) -> FailureClass:
        if isinstance(error, NonRecoverableNodeError):
            return "non_recoverable"
        if isinstance(error, TimeoutError):
            return "timeout"
        if isinstance(error, PermissionError):
            return "permission"
        if isinstance(error, ValueError):
            return "validation"
        error_name = type(error).__name__.lower()
        message = str(error).lower()
        if "rate" in message or "ratelimit" in error_name or "rate" in error_name:
            return "rate_limit"
        if "timeout" in message or "timeout" in error_name:
            return "timeout"
        if "connection" in message or "dependency" in message:
            return "dependency"
        if isinstance(error, RecoverableNodeError):
            return "semantic"
        return "unknown"


class RetryManager:
    """Reusable retry/fallback manager for LangGraph node execution."""

    def __init__(
        self,
        *,
        policy: RetryPolicy | None = None,
        classifier: ErrorClassifier | None = None,
    ) -> None:
        self.policy = policy or RetryPolicy()
        self.classifier = classifier or ErrorClassifier()

    def next_attempt(self, state: InvestigationState, node: str) -> int:
        return state.get("retry_counts", {}).get(node, 0) + 1

    def is_recoverable(self, failure_class: FailureClass, attempt: int) -> bool:
        return (
            failure_class in self.policy.recoverable_failure_classes
            and failure_class != "non_recoverable"
            and attempt < self.policy.max_attempts
        )

    async def execute(
        self,
        *,
        node: str,
        state: InvestigationState,
        handler: NodeHandler,
        fallback: NodeHandler | None = None,
    ) -> PartialState:
        attempt = self.next_attempt(state, node)
        try:
            result = await handler(state)
            return self._success(node=node, state=state, result=result, attempt=attempt)
        except Exception as exc:
            failure_class = self.classifier.classify(exc)
            recoverable = self.is_recoverable(failure_class, attempt)
            error = self._error(
                node=node,
                error=exc,
                attempt=attempt,
                failure_class=failure_class,
                recoverable=recoverable,
            )

            if recoverable:
                return self._retry(node=node, state=state, error=error, attempt=attempt)

            if fallback is not None:
                return await self._fallback(
                    node=node,
                    state=state,
                    fallback=fallback,
                    error=error,
                    attempt=attempt,
                )

            return self._failure(node=node, state=state, error=error, attempt=attempt)

    def _success(
        self,
        *,
        node: str,
        state: InvestigationState,
        result: PartialState,
        attempt: int,
    ) -> PartialState:
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[node] = attempt
        retry_state = dict(state.get("retry_state", {}))
        retry_state[node] = self._retry_state(
            node=node,
            attempt=attempt,
            retryable=False,
            exhausted=False,
        )
        result.setdefault("retry_counts", retry_counts)
        result.setdefault("retry_state", retry_state)
        result.setdefault("workflow_history", [])
        result["workflow_history"].append(_event(node, "completed", "Node completed successfully."))
        result.setdefault("node_results", [])
        result["node_results"].append(
            _node_result(node, "success", sorted(key for key in result if key != "node_results"))
        )
        return result

    def _retry(
        self,
        *,
        node: str,
        state: InvestigationState,
        error: NodeError,
        attempt: int,
    ) -> PartialState:
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[node] = attempt
        return {
            "status": self.policy.retry_route,
            "next_route": self.policy.retry_route,
            "retry_counts": retry_counts,
            "retry_state": {
                **state.get("retry_state", {}),
                node: self._retry_state(
                    node=node,
                    attempt=attempt,
                    retryable=True,
                    exhausted=False,
                    error=error,
                    next_retry_route=self.policy.retry_route,
                ),
            },
            "node_errors": [error],
            "node_results": [
                _node_result(
                    node,
                    "retrying",
                    ["status", "next_route", "node_errors", "retry_state"],
                    next_route=self.policy.retry_route,
                    error=error,
                )
            ],
            "workflow_history": [
                _event(
                    node,
                    "failed",
                    f"Recoverable {error.get('failure_class', 'unknown')} failure routed to "
                    f"{self.policy.retry_route}.",
                )
            ],
        }

    async def _fallback(
        self,
        *,
        node: str,
        state: InvestigationState,
        fallback: NodeHandler,
        error: NodeError,
        attempt: int,
    ) -> PartialState:
        fallback_result = await fallback(state)
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[node] = attempt
        fallback_name = self.policy.fallback_name or "deterministic_fallback"
        fallback_used = dict(state.get("fallback_used", {}))
        fallback_used[node] = fallback_name
        fallback_result["retry_counts"] = retry_counts
        fallback_result["retry_state"] = {
            **state.get("retry_state", {}),
            node: self._retry_state(
                node=node,
                attempt=attempt,
                retryable=False,
                exhausted=True,
                error=error,
                fallback_used=fallback_name,
            ),
        }
        fallback_result["fallback_used"] = fallback_used
        fallback_result.setdefault("node_errors", [])
        fallback_result["node_errors"].append(error)
        fallback_result.setdefault("node_results", [])
        fallback_result["node_results"].append(
            _node_result(
                node,
                "fallback",
                sorted(key for key in fallback_result if key != "node_results"),
                error=error,
            )
        )
        fallback_result.setdefault("workflow_history", [])
        fallback_result["workflow_history"].append(
            _event(
                node,
                "fallback",
                f"Fallback {fallback_name} completed after retry exhaustion or "
                "non-retryable failure.",
            )
        )
        return fallback_result

    def _failure(
        self,
        *,
        node: str,
        state: InvestigationState,
        error: NodeError,
        attempt: int,
    ) -> PartialState:
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[node] = attempt
        return {
            "status": "failed",
            "next_route": self.policy.failure_route,
            "retry_counts": retry_counts,
            "retry_state": {
                **state.get("retry_state", {}),
                node: self._retry_state(
                    node=node,
                    attempt=attempt,
                    retryable=False,
                    exhausted=True,
                    error=error,
                ),
            },
            "node_errors": [error],
            "node_results": [
                _node_result(
                    node,
                    "failed",
                    ["status", "next_route", "node_errors", "retry_state"],
                    next_route=self.policy.failure_route,
                    error=error,
                )
            ],
            "workflow_history": [
                _event(
                    node,
                    "failed",
                    f"Unrecoverable {error.get('failure_class', 'unknown')} failure routed to "
                    f"{self.policy.failure_route}.",
                )
            ],
        }

    def _error(
        self,
        *,
        node: str,
        error: Exception,
        attempt: int,
        failure_class: FailureClass,
        recoverable: bool,
    ) -> NodeError:
        return {
            "node": node,
            "error_type": type(error).__name__,
            "message": str(error),
            "retryable": recoverable,
            "attempt": attempt,
            "failure_class": failure_class,
            "recoverable": recoverable,
        }

    def _retry_state(
        self,
        *,
        node: str,
        attempt: int,
        retryable: bool,
        exhausted: bool,
        error: NodeError | None = None,
        next_retry_route: str | None = None,
        fallback_used: str | None = None,
    ) -> RetryState:
        retry_state: RetryState = {
            "node": node,
            "attempts": attempt,
            "max_attempts": self.policy.max_attempts,
            "retryable": retryable,
            "exhausted": exhausted,
        }
        if error is not None:
            retry_state["last_error_type"] = error["error_type"]
            if "failure_class" in error:
                retry_state["last_failure_class"] = error["failure_class"]
        if next_retry_route is not None:
            retry_state["next_retry_route"] = next_retry_route
        if fallback_used is not None:
            retry_state["fallback_used"] = fallback_used
        return retry_state


async def with_node_resilience(
    node: str,
    state: InvestigationState,
    handler: NodeHandler,
    fallback: NodeHandler | None = None,
    *,
    policy: RetryPolicy | None = None,
) -> PartialState:
    """Execute a LangGraph node with enterprise retry, fallback, and logging metadata."""

    return await RetryManager(policy=policy).execute(
        node=node,
        state=state,
        handler=handler,
        fallback=fallback,
    )
