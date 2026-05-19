from typing import NotRequired, TypedDict


Scalar = str | int | float | bool | None


class TransactionContext(TypedDict):
    """Normalized transaction context used across investigation branches."""

    transaction_id: str
    amount: float
    currency: str
    jurisdiction: str
    channel: NotRequired[str]
    occurred_at: NotRequired[str]
    merchant_id: NotRequired[str]
    device_id: NotRequired[str]
    raw_snapshot_ref: NotRequired[str]


class SubjectProfile(TypedDict):
    """Customer, account, and merchant context used for risk analysis."""

    customer_id: str
    account_ids: list[str]
    kyc_status: str
    customer_segment: NotRequired[str]
    merchant_id: NotRequired[str]
    merchant_category: NotRequired[str]
    profile_attributes: NotRequired[dict[str, Scalar]]


class ComplianceReviewState(TypedDict):
    """Compliance review state for sanctions, AML, PEP, and reporting checks."""

    sanctions_screened: bool
    pep_screened: bool
    aml_rules_evaluated: bool
    jurisdiction_checked: bool
    flags: list[str]
    policy_version: str
    reviewer_notes: NotRequired[list[str]]


class InvestigationMemory(TypedDict):
    """Persistent memory references available to future graph invocations."""

    memory_namespace: str
    case_memory_refs: list[str]
    entity_memory_refs: list[str]
    vector_collection: NotRequired[str]
    graph_snapshot_ref: NotRequired[str]
    last_updated_at: NotRequired[str]
