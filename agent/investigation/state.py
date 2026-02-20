"""Investigation state — the typed state object that flows through the LangGraph."""

from __future__ import annotations

from typing import Annotated, TypedDict

from agent.framing.models import ProblemFrame
from agent.hypothesis.models import Hypothesis
from agent.ingestion.models import NormalizedAlert


def _merge_lists(left: list, right: list) -> list:
    return left + right


class InvestigationState(TypedDict, total=False):
    # Input
    alert: NormalizedAlert

    # Enrichment
    context: dict
    runbook_context: list[str]
    past_incidents: list[str]
    correlation: dict

    # Framing
    problem_frame: ProblemFrame

    # Hypotheses
    hypotheses: list[Hypothesis]

    # Investigation
    evidence: Annotated[list[dict], _merge_lists]
    iteration: int
    max_iterations: int

    # Analysis
    root_cause_found: bool
    confidence: float

    # Output
    rca_report: dict
    status: str  # "investigating", "resolved", "escalated"
    error: str
