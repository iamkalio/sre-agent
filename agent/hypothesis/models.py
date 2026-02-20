"""Data models for hypotheses."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class HypothesisStatus(str, Enum):
    PENDING = "pending"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class InvestigationQuery(BaseModel):
    """A concrete query the agent plans to execute to test a hypothesis."""

    tool: str  # "prometheus", "loki", "tempo"
    query: str
    purpose: str


class Hypothesis(BaseModel):
    """A single root-cause hypothesis with its test plan."""

    id: str
    title: str
    description: str
    likelihood: float = Field(ge=0.0, le=1.0)
    status: HypothesisStatus = HypothesisStatus.PENDING
    supporting_evidence: list[str] = []
    contradicting_evidence: list[str] = []
    queries: list[InvestigationQuery] = []
    verdict: str = ""
