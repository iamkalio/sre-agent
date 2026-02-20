"""Investigation artifact storage — persists reports and feeds back into knowledge."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from agent.enrichment.knowledge import KnowledgeStore

logger = logging.getLogger("agent.reporting")

_ARTIFACTS_DIR = Path("/opt/agent/data/artifacts")


class ArtifactStore:
    """Persist investigation reports and feed resolved incidents back into knowledge."""

    def __init__(self, knowledge: KnowledgeStore | None) -> None:
        self._knowledge = knowledge
        _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: dict) -> str:
        """Save an RCA report to disk and return the file path."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        investigation_id = report.get("investigation_id", "unknown")
        filename = f"rca_{investigation_id}_{ts}.json"
        filepath = _ARTIFACTS_DIR / filename

        filepath.write_text(json.dumps(report, indent=2, default=str))
        logger.info("Report saved: %s", filepath)
        return str(filepath)

    def feed_back_to_knowledge(self, report: dict) -> None:
        """Store a resolved incident summary in the knowledge base for future RAG."""
        if report.get("status") != "resolved":
            return

        summary = (
            f"Incident: {report.get('title', 'Unknown')}\n"
            f"Alert: {report.get('alert_name', 'Unknown')}\n"
            f"Root Cause: {report.get('root_cause', 'Unknown')}\n"
            f"Resolution: {'; '.join(report.get('recommended_actions', []))}\n"
            f"Confidence: {report.get('confidence', 0):.0%}\n"
        )

        if not self._knowledge:
            return

        self._knowledge.store_incident(
            incident_id=report.get("investigation_id", "unknown"),
            summary=summary,
            metadata={
                "alert_name": report.get("alert_name", ""),
                "severity": report.get("severity", ""),
                "confidence": report.get("confidence", 0),
            },
        )
        logger.info("Incident fed back to knowledge store: %s", report.get("title"))

    def list_reports(self, limit: int = 20) -> list[dict]:
        """List recent investigation reports."""
        files = sorted(_ARTIFACTS_DIR.glob("rca_*.json"), reverse=True)[:limit]
        reports = []
        for f in files:
            try:
                reports.append(json.loads(f.read_text()))
            except Exception:
                logger.exception("Failed to read report: %s", f)
        return reports

    def get_report(self, investigation_id: str) -> dict | None:
        """Retrieve a specific report by investigation ID."""
        for f in _ARTIFACTS_DIR.glob(f"rca_{investigation_id}_*.json"):
            try:
                return json.loads(f.read_text())
            except Exception:
                logger.exception("Failed to read report: %s", f)
        return None
