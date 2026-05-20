import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from uuid import uuid4

from app.core.graph.state_schemas import (
    FinancialDocument,
    FinancialDocumentChunk,
    FinancialDocumentType,
    FinancialRetrievalResponse,
    RetrievalCitation,
    RetrievalEvidence,
    RetrievalResult,
)

TokenVector = dict[str, float]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _cosine(left: TokenVector, right: TokenVector) -> float:
    common = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _short_quote(text: str, max_chars: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3]}..."


@dataclass(frozen=True)
class RetrievalPolicy:
    chunk_size_words: int = 120
    chunk_overlap_words: int = 25
    top_k: int = 5
    min_grounding_score: float = 0.12
    document_type_boost: float = 0.08


class HashingEmbeddingProvider:
    """Deterministic local embedding fallback for tests and offline development."""

    async def embed(self, text: str) -> TokenVector:
        counts = Counter(_tokens(text))
        return {token: float(count) for token, count in counts.items()}


class FinancialDocumentIngestionPipeline:
    """Chunks normalized financial documents into retrieval units."""

    def __init__(self, policy: RetrievalPolicy | None = None) -> None:
        self._policy = policy or RetrievalPolicy()

    def ingest(self, documents: list[FinancialDocument]) -> list[FinancialDocumentChunk]:
        chunks: list[FinancialDocumentChunk] = []
        for document in documents:
            words = document["text"].split()
            if not words:
                continue
            step = max(1, self._policy.chunk_size_words - self._policy.chunk_overlap_words)
            for chunk_index, start in enumerate(range(0, len(words), step)):
                chunk_words = words[start : start + self._policy.chunk_size_words]
                chunk_text = " ".join(chunk_words)
                chunk_hash = hashlib.sha1(
                    f"{document['document_id']}:{chunk_index}:{chunk_text}".encode("utf-8")
                ).hexdigest()[:16]
                chunks.append(
                    {
                        "chunk_id": f"chunk_{chunk_hash}",
                        "document_id": document["document_id"],
                        "title": document["title"],
                        "document_type": document["document_type"],
                        "source_uri": document["source_uri"],
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "page_number": document.get("metadata", {}).get("page_number"),
                        "section": document.get("metadata", {}).get("section"),
                        "metadata": document.get("metadata", {}),
                    }
                )
        return chunks


class InMemoryVectorRetrievalLayer:
    """Async vector retrieval layer that can be replaced by pgvector or external search."""

    def __init__(self, embedding_provider: HashingEmbeddingProvider | None = None) -> None:
        self._embedding_provider = embedding_provider or HashingEmbeddingProvider()
        self._chunks: list[FinancialDocumentChunk] = []
        self._embeddings: dict[str, TokenVector] = {}

    async def index(self, chunks: list[FinancialDocumentChunk]) -> None:
        self._chunks = list(chunks)
        self._embeddings = {
            chunk["chunk_id"]: await self._embedding_provider.embed(chunk["text"])
            for chunk in chunks
        }

    async def search(
        self,
        query: str,
        *,
        top_k: int,
        document_types: list[FinancialDocumentType] | None = None,
    ) -> list[tuple[FinancialDocumentChunk, float]]:
        query_embedding = await self._embedding_provider.embed(query)
        scored: list[tuple[FinancialDocumentChunk, float]] = []
        for chunk in self._chunks:
            if document_types and chunk["document_type"] not in document_types:
                continue
            score = _cosine(query_embedding, self._embeddings.get(chunk["chunk_id"], {}))
            scored.append((chunk, round(score, 4)))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


class FinancialReranker:
    """Deterministic reranker blending semantic, keyword, type, and grounding signals."""

    def rerank(
        self,
        *,
        query: str,
        candidates: list[tuple[FinancialDocumentChunk, float]],
        preferred_document_types: list[FinancialDocumentType] | None = None,
        policy: RetrievalPolicy,
    ) -> list[RetrievalResult]:
        query_tokens = set(_tokens(query))
        results: list[RetrievalResult] = []
        for chunk, embedding_score in candidates:
            chunk_tokens = set(_tokens(chunk["text"]))
            keyword_score = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
            type_boost = (
                policy.document_type_boost
                if preferred_document_types and chunk["document_type"] in preferred_document_types
                else 0.0
            )
            grounding_score = min(1.0, embedding_score * 0.6 + keyword_score * 0.4)
            rerank_score = min(1.0, embedding_score * 0.5 + keyword_score * 0.35 + type_boost)
            citation = self._citation(chunk)
            results.append(
                {
                    "chunk": chunk,
                    "embedding_score": embedding_score,
                    "keyword_score": round(keyword_score, 4),
                    "rerank_score": round(rerank_score, 4),
                    "grounding_score": round(grounding_score, 4),
                    "citation": citation,
                }
            )
        return sorted(results, key=lambda item: item["rerank_score"], reverse=True)

    def _citation(self, chunk: FinancialDocumentChunk) -> RetrievalCitation:
        location = chunk.get("section") or f"chunk {chunk['chunk_index']}"
        return {
            "citation_id": f"cite_{uuid4().hex}",
            "document_id": chunk["document_id"],
            "chunk_id": chunk["chunk_id"],
            "title": chunk["title"],
            "source_uri": chunk["source_uri"],
            "document_type": chunk["document_type"],
            "page_number": chunk.get("page_number"),
            "section": chunk.get("section"),
            "quote": _short_quote(chunk["text"]),
            "attribution": f"{chunk['title']} ({chunk['document_type']}, {location})",
        }


class EvidenceGroundingPipeline:
    """Builds grounded evidence records from reranked retrieval results."""

    def ground(
        self,
        *,
        query: str,
        results: list[RetrievalResult],
        min_grounding_score: float,
    ) -> list[RetrievalEvidence]:
        evidence: list[RetrievalEvidence] = []
        for result in results:
            if result["grounding_score"] < min_grounding_score:
                continue
            evidence.append(
                {
                    "evidence_id": f"retrieval_ev_{uuid4().hex}",
                    "claim": f"Retrieved support for query: {query}",
                    "citation": result["citation"],
                    "relevance_score": result["embedding_score"],
                    "rerank_score": result["rerank_score"],
                    "grounding_score": result["grounding_score"],
                }
            )
        return evidence


class FinancialRetrievalAgentService:
    """Production-style RAG service with ingestion, retrieval, reranking, and citations."""

    def __init__(
        self,
        *,
        policy: RetrievalPolicy | None = None,
        ingestion: FinancialDocumentIngestionPipeline | None = None,
        vector_layer: InMemoryVectorRetrievalLayer | None = None,
        reranker: FinancialReranker | None = None,
        grounding: EvidenceGroundingPipeline | None = None,
    ) -> None:
        self._policy = policy or RetrievalPolicy()
        self._ingestion = ingestion or FinancialDocumentIngestionPipeline(self._policy)
        self._vector_layer = vector_layer or InMemoryVectorRetrievalLayer()
        self._reranker = reranker or FinancialReranker()
        self._grounding = grounding or EvidenceGroundingPipeline()
        self._indexed = False

    async def ingest_documents(
        self,
        documents: list[FinancialDocument],
    ) -> list[FinancialDocumentChunk]:
        chunks = self._ingestion.ingest(documents)
        await self._vector_layer.index(chunks)
        self._indexed = True
        return chunks

    async def retrieve(
        self,
        *,
        query: str,
        documents: list[FinancialDocument] | None = None,
        document_types: list[FinancialDocumentType] | None = None,
        retrieval_intent: str = "financial_investigation",
    ) -> FinancialRetrievalResponse:
        if documents is not None or not self._indexed:
            await self.ingest_documents(documents or default_financial_documents())
        candidates = await self._vector_layer.search(
            query,
            top_k=max(self._policy.top_k * 3, self._policy.top_k),
            document_types=document_types,
        )
        reranked = self._reranker.rerank(
            query=query,
            candidates=candidates,
            preferred_document_types=document_types,
            policy=self._policy,
        )[: self._policy.top_k]
        evidence = self._grounding.ground(
            query=query,
            results=reranked,
            min_grounding_score=self._policy.min_grounding_score,
        )
        citations = [result["citation"] for result in reranked]
        confidence = self._confidence(reranked, evidence)
        return {
            "query": query,
            "retrieval_intent": retrieval_intent,
            "results": reranked,
            "evidence": evidence,
            "citations": citations,
            "confidence": confidence,
            "answer_summary": self._summary(query, evidence),
            "source_attribution": [citation["attribution"] for citation in citations],
            "recommended_actions": self._actions(confidence, evidence),
        }

    def _confidence(
        self,
        results: list[RetrievalResult],
        evidence: list[RetrievalEvidence],
    ) -> float:
        if not results:
            return 0.0
        avg_rerank = sum(result["rerank_score"] for result in results) / len(results)
        evidence_factor = min(0.25, len(evidence) * 0.05)
        return round(min(0.95, avg_rerank * 0.75 + evidence_factor), 2)

    def _summary(self, query: str, evidence: list[RetrievalEvidence]) -> str:
        if not evidence:
            return f"No grounded financial evidence retrieved for query: {query}"
        titles = []
        for item in evidence:
            title = item["citation"]["title"]
            if title not in titles:
                titles.append(title)
        return f"Retrieved {len(evidence)} grounded evidence items from {', '.join(titles[:3])}."

    def _actions(
        self,
        confidence: float,
        evidence: list[RetrievalEvidence],
    ) -> list[str]:
        if confidence >= 0.7 and evidence:
            return ["attach_citations", "ground_investigation_findings"]
        if evidence:
            return ["analyst_review_retrieved_sources"]
        return ["expand_retrieval_query", "request_additional_documents"]


def default_financial_documents() -> list[FinancialDocument]:
    return [
        {
            "document_id": "sec_10k_controls_001",
            "title": "Example Form 10-K Internal Controls Disclosure",
            "document_type": "sec_filing",
            "source_uri": "sec://filings/example-10k-controls",
            "issuer": "Example Financial Holdings",
            "jurisdiction": "US",
            "text": (
                "Management assessed internal control over financial reporting and disclosed "
                "material weaknesses related to transaction monitoring, reconciliation, and "
                "timely escalation of suspicious activity exceptions."
            ),
            "metadata": {"section": "Item 9A Controls and Procedures", "page_number": 92},
        },
        {
            "document_id": "aml_guidance_001",
            "title": "AML Monitoring Guidance",
            "document_type": "aml_guidance",
            "source_uri": "policy://aml/monitoring-guidance",
            "jurisdiction": "US",
            "text": (
                "AML programs should monitor structuring, rapid movement of funds, unusual "
                "counterparty concentration, cross-border activity, and transactions inconsistent "
                "with customer risk profiles."
            ),
            "metadata": {"section": "Suspicious Activity Monitoring", "page_number": 14},
        },
        {
            "document_id": "compliance_policy_001",
            "title": "Enterprise Compliance Escalation Policy",
            "document_type": "compliance_policy",
            "source_uri": "policy://compliance/escalation",
            "jurisdiction": "US",
            "text": (
                "High-risk investigations require evidence grounding, documented rationale, "
                "source citations, and senior compliance approval before final escalation or "
                "temporary account restriction."
            ),
            "metadata": {"section": "Escalation Requirements", "page_number": 6},
        },
        {
            "document_id": "audit_report_001",
            "title": "Transaction Monitoring Audit Report",
            "document_type": "audit_report",
            "source_uri": "audit://reports/transaction-monitoring",
            "text": (
                "The audit found inconsistent evidence retention for fraud alerts and recommended "
                "linking alert decisions to policy citations, transaction chains, and reviewer "
                "approval records."
            ),
            "metadata": {"section": "Findings", "page_number": 22},
        },
        {
            "document_id": "governance_report_001",
            "title": "Financial Crime Governance Report",
            "document_type": "governance_report",
            "source_uri": "governance://financial-crime/report",
            "text": (
                "Governance committees require transparent metrics for alert quality, escalation "
                "timeliness, investigation replay, and traceable evidence used by automated agents."
            ),
            "metadata": {"section": "Board Reporting", "page_number": 9},
        },
    ]
