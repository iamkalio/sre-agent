"""SRE Agent — FastAPI service entry point."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.config import settings
from agent.enrichment.context import ContextBuilder
from agent.enrichment.correlator import SignalCorrelator
from agent.enrichment.knowledge import KnowledgeStore
from agent.ingestion.models import NormalizedAlert
from agent.ingestion.receiver import register_investigation_callback, router as alert_router
from agent.investigation.executor import InvestigationExecutor
from agent.investigation.graph import compile_investigation_graph
from agent.investigation.tools.loki import LokiClient
from agent.investigation.tools.prometheus import PrometheusClient
from agent.investigation.tools.tempo import TempoClient
from agent.reporting.artifacts import ArtifactStore

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)
logger = logging.getLogger("agent")

# ── Singletons initialised at startup ─────────────────────────────

knowledge: KnowledgeStore | None = None
artifacts: ArtifactStore | None = None
_compiled_graph = None
_correlator: SignalCorrelator | None = None
_prometheus: PrometheusClient | None = None
_loki: LokiClient | None = None
_tempo: TempoClient | None = None


def _build_llm():
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=4096,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global knowledge, artifacts, _compiled_graph
    global _correlator, _prometheus, _loki, _tempo

    logger.info("Initializing SRE Agent...")

    # Knowledge store (non-fatal — agent can still operate without runbooks)
    try:
        knowledge = KnowledgeStore()
        count = knowledge.ingest_runbooks()
        logger.info("Loaded %d runbook chunks into knowledge store", count)
    except Exception:
        logger.exception("Knowledge store initialization failed — continuing without runbooks")
        knowledge = None

    # Observability clients
    _prometheus = PrometheusClient()
    _loki = LokiClient()
    _tempo = TempoClient()
    _correlator = SignalCorrelator()

    # Enrichment
    context_builder = ContextBuilder(knowledge, _correlator)

    # Investigation executor
    executor = InvestigationExecutor(_prometheus, _loki, _tempo)

    # LLM + Graph
    llm = _build_llm()
    _compiled_graph = compile_investigation_graph(llm, context_builder, executor)

    # Artifact store
    artifacts = ArtifactStore(knowledge)

    # Wire up the investigation callback
    register_investigation_callback(_run_investigation)

    logger.info("SRE Agent ready — listening on %s:%d", settings.host, settings.port)

    yield

    # Cleanup
    await _correlator.close()
    await _prometheus.close()
    await _loki.close()
    await _tempo.close()
    logger.info("SRE Agent shut down")


async def _run_investigation(alert: NormalizedAlert) -> None:
    """Execute a full investigation for a normalized alert."""
    logger.info("Starting investigation for alert=%s name=%s", alert.id, alert.name)

    try:
        initial_state = {
            "alert": alert,
            "evidence": [],
            "iteration": 0,
            "max_iterations": settings.max_investigation_iterations,
            "root_cause_found": False,
            "confidence": 0.0,
            "status": "investigating",
        }

        result = await _compiled_graph.ainvoke(initial_state)

        report = result.get("rca_report", {})
        if artifacts:
            artifacts.save_report(report)
            artifacts.feed_back_to_knowledge(report)

        logger.info(
            "Investigation complete: alert=%s status=%s confidence=%.0f%%",
            alert.id,
            result.get("status", "unknown"),
            result.get("confidence", 0) * 100,
        )

    except Exception:
        logger.exception("Investigation failed for alert=%s", alert.id)


# ── FastAPI app ───────────────────────────────────────────────────

app = FastAPI(
    title="SRE Investigation Agent",
    description="AI-powered alert investigation, RCA, and incident analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(alert_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "knowledge_loaded": knowledge is not None,
        "graph_ready": _compiled_graph is not None,
    }


@app.get("/reports")
async def list_reports(limit: int = 20):
    if artifacts:
        return {"reports": artifacts.list_reports(limit=limit)}
    return {"reports": []}


@app.get("/reports/{investigation_id}")
async def get_report(investigation_id: str):
    if artifacts:
        report = artifacts.get_report(investigation_id)
        if report:
            return report
    return {"error": "Report not found"}
