"""RCA report generator — LLM synthesizes investigation results into a structured report."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger("agent.reporting")

_SYSTEM_PROMPT = """\
You are an expert SRE writing a Root Cause Analysis report. Synthesize the entire \
investigation into a clear, actionable report.

Respond ONLY with valid JSON matching this schema:
{
  "title": "concise incident title",
  "summary": "2-3 sentence executive summary",
  "root_cause": "detailed root cause explanation",
  "impact": "what was affected and how",
  "timeline": [
    {"timestamp": "ISO timestamp or relative", "event": "what happened", "source": "metrics/logs/traces"}
  ],
  "evidence": [
    {"tool": "prometheus/loki/tempo", "query": "the query", "purpose": "why we ran it", "finding": "what it showed"}
  ],
  "recommended_actions": ["action 1", "action 2"],
  "runbook_references": ["relevant runbook names"]
}

Be specific. Reference actual metric values, log messages, and trace IDs when available.
"""


async def generate_rca_report(llm: BaseChatModel, state: dict) -> dict:
    """Generate a structured RCA report from the full investigation state."""
    alert = state.get("alert", {})
    if hasattr(alert, "model_dump"):
        alert = alert.model_dump(mode="json")

    hypotheses = state.get("hypotheses", [])
    hyp_data = [h.model_dump() if hasattr(h, "model_dump") else h for h in hypotheses]

    user_content = (
        f"Alert:\n{json.dumps(alert, default=str)}\n\n"
        f"Problem frame:\n{json.dumps(state.get('problem_frame', {}), default=str)}\n\n"
        f"Hypotheses:\n{json.dumps(hyp_data, default=str)}\n\n"
        f"Evidence gathered:\n{json.dumps(state.get('evidence', []), default=str)}\n\n"
        f"Runbook context:\n{chr(10).join(state.get('runbook_context', []))}\n\n"
        f"Correlation data:\n{json.dumps(state.get('correlation', {}), default=str)}"
    )

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    report = json.loads(raw)

    alert_obj = state.get("alert")
    report["investigation_id"] = getattr(alert_obj, "id", "unknown")
    report["alert_name"] = getattr(alert_obj, "name", alert.get("name", "unknown"))
    report["severity"] = getattr(alert_obj, "severity", alert.get("severity", "unknown"))
    if hasattr(report["severity"], "value"):
        report["severity"] = report["severity"].value
    report["status"] = state.get("status", "resolved")
    report["confidence"] = state.get("confidence", 0.0)
    report["iterations"] = state.get("iteration", 0)
    report["hypotheses_evaluated"] = len(hypotheses)
    report["hypotheses_confirmed"] = [
        h.title if hasattr(h, "title") else h.get("title", "")
        for h in hypotheses
        if (h.status.value if hasattr(h, "status") and hasattr(h.status, "value") else h.get("status")) == "confirmed"
    ]
    report["hypotheses_rejected"] = [
        h.title if hasattr(h, "title") else h.get("title", "")
        for h in hypotheses
        if (h.status.value if hasattr(h, "status") and hasattr(h.status, "value") else h.get("status")) == "rejected"
    ]

    logger.info("RCA report generated: %s (confidence=%.0f%%)", report["title"], report["confidence"] * 100)
    return report
