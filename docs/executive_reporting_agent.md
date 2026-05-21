# Executive Reporting Agent

The Executive Reporting Agent converts structured investigation state into enterprise-ready reports
with executive summaries, audit explanations, escalation summaries, evidence-backed findings,
citations, and confidence metadata.

## 1. Reporting Architecture

```text
LangGraph reporting_agent_node
  -> ExecutiveReportingService
      -> citation collector
      -> finding formatter
      -> executive summary pipeline
      -> risk and escalation summary pipeline
      -> audit explanation pipeline
      -> markdown renderer
  -> InvestigationState partial update
```

Implementation files:

```text
app/core/graph/state_schemas/reporting.py
app/services/reporting.py
app/core/graph/reporting_agent_node.py
examples/run_reporting_agent.py
```

## 2. Report Templates

The primary typed output is `ExecutiveReport`.

Sections include:

- executive summary
- investigation summary
- risk summary
- escalation summary
- audit explanation
- evidence summary
- evidence-backed findings
- citations
- recommended actions

The service also renders a Markdown `report_draft` for compatibility with existing report workflow
state.

## 3. Evidence Formatting Strategy

Findings are formatted as `ReportFinding` records:

```text
finding_id
severity
title
summary
evidence_ids
citation_ids
confidence
```

The reporting service derives findings from:

- fraud detection
- compliance validation
- operational risk
- critic validation

## 4. Citation Integration

Citations are collected from:

- financial retrieval citations
- compliance validation citations

Each `ReportCitation` includes:

```text
citation_id
title
source_uri
attribution
quote
```

Citations are deduplicated by citation ID and attached to report findings and sections.

## 5. Executive Summary Pipeline

The summary pipeline generates:

- concise executive summary
- investigation scope
- operational risk summary
- escalation rationale
- audit explanation
- evidence and citation counts

Confidence is calculated from finding confidence, citation count, and critic validation status.

## 6. LangGraph Integration

`reporting_agent_node(...)` writes:

- `executive_report`
- `report_draft`
- `final_report_uri`
- `agent_executions`
- `workflow_history`
- terminal `closed` status when report confidence is ready for review

Run the example:

```bash
python examples/run_reporting_agent.py
```

## Enterprise Notes

- Keep structured report output separate from rendered report text.
- Include citations in every high-impact report.
- Use critic validation status to influence report confidence.
- Persist report metadata for audit and replay.
- Treat final external distribution as a separate controlled workflow action.
