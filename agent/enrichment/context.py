"""Context builder — assembles full investigation context from all sources."""

from __future__ import annotations

import logging

from agent.enrichment.correlator import SignalCorrelator
from agent.enrichment.knowledge import KnowledgeStore
from agent.ingestion.models import NormalizedAlert

logger = logging.getLogger("agent.enrichment")


class ContextBuilder:
    """Assembles enrichment context for an alert: knowledge + live signal correlation."""

    def __init__(self, knowledge: KnowledgeStore | None, correlator: SignalCorrelator) -> None:
        self._knowledge = knowledge
        self._correlator = correlator

    async def build(self, alert: NormalizedAlert) -> dict:
        search_query = f"{alert.name} {alert.summary} {alert.description}"

        runbooks = self._knowledge.search_runbooks(search_query) if self._knowledge else []
        past_incidents = self._knowledge.search_incidents(search_query) if self._knowledge else []
        correlation = await self._correlator.correlate(alert.name, alert.starts_at)

        context = {
            "alert": alert.model_dump(mode="json"),
            "runbook_context": [r["content"] for r in runbooks],
            "past_incidents": [i["content"] for i in past_incidents],
            "correlation": correlation,
        }

        logger.info(
            "Context built for alert=%s: %d runbook chunks, %d past incidents, "
            "%d error logs, %d traces",
            alert.id,
            len(runbooks),
            len(past_incidents),
            correlation.get("error_logs_count", 0),
            correlation.get("traces_found", 0),
        )
        return context
