"""Data models for RCA reports and investigation artifacts."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    timestamp: str
    event: str
    source: str = ""


class EvidenceItem(BaseModel):
    tool: str
    query: str
    purpose: str
    finding: str


class RCAReport(BaseModel):
    """Structured Root Cause Analysis report."""

    investigation_id: str
    alert_name: str
    severity: str
    status: str  # resolved / escalated
    title: str
    summary: str
    root_cause: str
    impact: str
    timeline: list[TimelineEntry] = []
    evidence: list[EvidenceItem] = []
    hypotheses_evaluated: int = 0
    hypotheses_confirmed: list[str] = []
    hypotheses_rejected: list[str] = []
    recommended_actions: list[str] = []
    runbook_references: list[str] = []
    confidence: float = 0.0
    investigation_duration_seconds: float = 0.0
    iterations: int = 0
    escalated: bool = False
    escalation_reason: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
