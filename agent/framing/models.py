"""Data models for problem framing."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ImpactLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProblemFrame(BaseModel):
    """Structured definition of the problem under investigation."""

    title: str
    what: str
    when: str
    where: str
    impact: ImpactLevel
    affected_components: list[str] = []
    initial_observations: list[str] = []
    investigation_scope: str = ""
    questions_to_answer: list[str] = []
