"""LangGraph investigation workflow — the core orchestration graph."""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from agent.enrichment.context import ContextBuilder
from agent.framing.framer import frame_problem
from agent.hypothesis.generator import generate_hypotheses
from agent.hypothesis.models import HypothesisStatus
from agent.hypothesis.ranker import rerank_hypotheses
from agent.investigation.executor import InvestigationExecutor
from agent.investigation.state import InvestigationState
from agent.reporting.rca import generate_rca_report

logger = logging.getLogger("agent.investigation")


def build_investigation_graph(
    llm: BaseChatModel,
    context_builder: ContextBuilder,
    executor: InvestigationExecutor,
) -> StateGraph:
    """Construct the LangGraph state machine for alert investigation."""

    # ── Node functions ──────────────────────────────────────────────

    async def enrich_context(state: InvestigationState) -> dict:
        alert = state["alert"]
        ctx = await context_builder.build(alert)
        return {
            "context": ctx,
            "runbook_context": ctx.get("runbook_context", []),
            "past_incidents": ctx.get("past_incidents", []),
            "correlation": ctx.get("correlation", {}),
            "status": "investigating",
            "iteration": 0,
        }

    async def frame(state: InvestigationState) -> dict:
        pf = await frame_problem(llm, state["context"])
        return {"problem_frame": pf}

    async def hypothesize(state: InvestigationState) -> dict:
        hyps = await generate_hypotheses(llm, state["problem_frame"], state["context"])
        return {"hypotheses": hyps}

    async def investigate(state: InvestigationState) -> dict:
        alert_time = state["alert"].starts_at
        evidence = await executor.execute_all(state["hypotheses"], alert_time)
        iteration = state.get("iteration", 0) + 1
        return {"evidence": evidence, "iteration": iteration}

    async def analyze(state: InvestigationState) -> dict:
        updated = await rerank_hypotheses(llm, state["hypotheses"], state["evidence"])

        confirmed = [h for h in updated if h.status == HypothesisStatus.CONFIRMED]
        best = max(updated, key=lambda h: h.likelihood) if updated else None
        confidence = best.likelihood if best else 0.0

        return {
            "hypotheses": updated,
            "root_cause_found": len(confirmed) > 0,
            "confidence": confidence,
        }

    async def report(state: InvestigationState) -> dict:
        rca = await generate_rca_report(llm, state)
        return {"rca_report": rca, "status": "resolved"}

    async def escalate(state: InvestigationState) -> dict:
        logger.warning(
            "Investigation escalated — confidence=%.2f after %d iterations",
            state.get("confidence", 0),
            state.get("iteration", 0),
        )
        rca = await generate_rca_report(llm, state)
        rca["escalated"] = True
        rca["escalation_reason"] = (
            f"Confidence {state.get('confidence', 0):.0%} below threshold after "
            f"{state.get('iteration', 0)} iterations"
        )
        return {"rca_report": rca, "status": "escalated"}

    # ── Routing logic ───────────────────────────────────────────────

    def should_continue(state: InvestigationState) -> Literal["report", "investigate", "escalate"]:
        if state.get("root_cause_found"):
            return "report"

        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", 6)
        if iteration >= max_iter:
            return "escalate"

        return "investigate"

    # ── Build the graph ─────────────────────────────────────────────

    graph = StateGraph(InvestigationState)

    graph.add_node("enrich_context", enrich_context)
    graph.add_node("frame", frame)
    graph.add_node("hypothesize", hypothesize)
    graph.add_node("investigate", investigate)
    graph.add_node("analyze", analyze)
    graph.add_node("report", report)
    graph.add_node("escalate", escalate)

    graph.set_entry_point("enrich_context")
    graph.add_edge("enrich_context", "frame")
    graph.add_edge("frame", "hypothesize")
    graph.add_edge("hypothesize", "investigate")
    graph.add_edge("investigate", "analyze")

    graph.add_conditional_edges("analyze", should_continue, {
        "report": "report",
        "investigate": "investigate",
        "escalate": "escalate",
    })

    graph.add_edge("report", END)
    graph.add_edge("escalate", END)

    return graph


def compile_investigation_graph(
    llm: BaseChatModel,
    context_builder: ContextBuilder,
    executor: InvestigationExecutor,
):
    """Build and compile the investigation graph, ready to invoke."""
    graph = build_investigation_graph(llm, context_builder, executor)
    return graph.compile()
