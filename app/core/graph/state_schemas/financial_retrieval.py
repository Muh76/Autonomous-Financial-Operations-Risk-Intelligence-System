from typing import Literal, NotRequired, TypedDict


FinancialDocumentType = Literal[
    "sec_filing",
    "audit_report",
    "compliance_policy",
    "aml_guidance",
    "governance_report",
]


class FinancialDocument(TypedDict):
    """Normalized source document for financial retrieval ingestion."""

    document_id: str
    title: str
    document_type: FinancialDocumentType
    source_uri: str
    published_at: NotRequired[str]
    issuer: NotRequired[str]
    jurisdiction: NotRequired[str]
    text: str
    metadata: NotRequired[dict[str, str | int | float | bool | None]]


class FinancialDocumentChunk(TypedDict):
    """Chunk-level retrieval unit with source attribution metadata."""

    chunk_id: str
    document_id: str
    title: str
    document_type: FinancialDocumentType
    source_uri: str
    text: str
    chunk_index: int
    page_number: NotRequired[int]
    section: NotRequired[str]
    metadata: NotRequired[dict[str, str | int | float | bool | None]]


class RetrievalCitation(TypedDict):
    """Citation emitted for grounded evidence and analyst review."""

    citation_id: str
    document_id: str
    chunk_id: str
    title: str
    source_uri: str
    document_type: FinancialDocumentType
    page_number: NotRequired[int]
    section: NotRequired[str]
    quote: str
    attribution: str


class RetrievalEvidence(TypedDict):
    """Grounded retrieval evidence with citation and relevance metadata."""

    evidence_id: str
    claim: str
    citation: RetrievalCitation
    relevance_score: float
    rerank_score: float
    grounding_score: float


class RetrievalResult(TypedDict):
    """One retrieved and reranked document chunk."""

    chunk: FinancialDocumentChunk
    embedding_score: float
    keyword_score: float
    rerank_score: float
    grounding_score: float
    citation: RetrievalCitation


class FinancialRetrievalResponse(TypedDict):
    """Typed response schema for the Financial Retrieval Agent."""

    query: str
    retrieval_intent: str
    results: list[RetrievalResult]
    evidence: list[RetrievalEvidence]
    citations: list[RetrievalCitation]
    confidence: float
    answer_summary: str
    source_attribution: list[str]
    recommended_actions: list[str]
