# Financial Retrieval Agent

The Financial Retrieval Agent is a production-style RAG subsystem for financial investigation
workflows. It retrieves and grounds evidence from SEC filings, audit reports, compliance policies,
AML guidance, and governance reports with citations, reranking, confidence scoring, and source
attribution.

## 1. Retrieval Architecture

```text
LangGraph financial_retrieval_node
  -> FinancialRetrievalAgentService
      -> document ingestion pipeline
      -> embedding provider
      -> vector retrieval layer
      -> reranking pipeline
      -> citation generator
      -> evidence grounding pipeline
  -> InvestigationState partial update
```

Implementation files:

```text
app/core/graph/state_schemas/financial_retrieval.py
app/services/financial_retrieval.py
app/core/graph/financial_retrieval_node.py
examples/run_financial_retrieval_agent.py
```

The default vector layer is an in-memory deterministic implementation for development and tests.
Production can replace it with pgvector, OpenSearch, Pinecone, Weaviate, or another governed vector
backend.

## 2. Document Ingestion Pipeline

The ingestion pipeline accepts normalized `FinancialDocument` records:

- SEC filings
- audit reports
- compliance policies
- AML guidance
- governance reports

Each document is chunked into `FinancialDocumentChunk` records with:

- chunk ID
- document ID
- source URI
- document type
- page number
- section
- text
- metadata

Raw documents should live in governed storage. Workflow state should keep only references, chunks,
citations, and grounded evidence.

## 3. Vector Retrieval Layer

The `InMemoryVectorRetrievalLayer` provides an async interface:

```text
index(chunks)
search(query, top_k, document_types)
```

The included `HashingEmbeddingProvider` is deterministic and dependency-free. It behaves like a
local embedding fallback for tests. Production implementations should preserve the same interface
while using approved embedding models and vector stores.

## 4. Reranking Architecture

`FinancialReranker` blends:

- embedding similarity
- keyword overlap
- preferred document type boost
- grounding score

This produces `RetrievalResult` records with:

```text
chunk
embedding_score
keyword_score
rerank_score
grounding_score
citation
```

The reranker is deterministic so enterprise QA can reproduce retrieval behavior.

## 5. Citation System

Each retrieved chunk emits `RetrievalCitation`:

```text
citation_id
document_id
chunk_id
title
source_uri
document_type
page_number
section
quote
attribution
```

Citations are source-attributed and suitable for analyst review, report generation, and audit
exports. The quote is intentionally short to keep workflow state compact.

## 6. Evidence Grounding Pipeline

`EvidenceGroundingPipeline` converts reranked results into `RetrievalEvidence` when the grounding
score clears policy thresholds.

Grounded evidence includes:

- claim
- citation
- relevance score
- rerank score
- grounding score

This keeps generated investigation claims tied to specific source documents.

## 7. LangGraph Node Integration

`financial_retrieval_node(...)` is LangGraph-compatible and writes:

- `financial_retrieval`
- `evidence`
- `findings`
- `agent_executions`
- `workflow_history`

The node uses `with_node_resilience(...)` for retry/fallback behavior.

Run the example:

```bash
python examples/run_financial_retrieval_agent.py
```

## Enterprise Notes

- Use governed embedding models.
- Version document indexes and embedding models.
- Store full documents outside workflow state.
- Persist citations and evidence as audit records.
- Enforce tenant and entitlement filtering before retrieval.
- Keep reranking deterministic or trace model-assisted reranking decisions.
- Require citations before report generation or human escalation packets.
