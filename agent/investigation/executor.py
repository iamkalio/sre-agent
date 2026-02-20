"""Investigation executor — runs queries from hypothesis test plans against backends."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from agent.config import settings
from agent.hypothesis.models import Hypothesis, InvestigationQuery
from agent.investigation.tools.loki import LokiClient
from agent.investigation.tools.prometheus import PrometheusClient
from agent.investigation.tools.tempo import TempoClient

logger = logging.getLogger("agent.investigation")


class InvestigationExecutor:
    """Executes the query plan for a set of hypotheses against live backends."""

    def __init__(
        self,
        prometheus: PrometheusClient,
        loki: LokiClient,
        tempo: TempoClient,
    ) -> None:
        self._prometheus = prometheus
        self._loki = loki
        self._tempo = tempo

    async def execute_query(
        self, query: InvestigationQuery, alert_time: datetime
    ) -> dict:
        """Execute a single investigation query against the appropriate backend."""
        start = alert_time - timedelta(minutes=settings.query_lookback_minutes)
        end = alert_time + timedelta(minutes=settings.query_lookahead_minutes)

        try:
            if query.tool == "prometheus":
                result = await self._prometheus.range_query(query.query, start=start, end=end)
            elif query.tool == "loki":
                result = await self._loki.query_range(query.query, start=start, end=end)
            elif query.tool == "tempo":
                result = await self._tempo.search(tags=query.query, start=start, end=end)
            else:
                return {"tool": query.tool, "error": f"Unknown tool: {query.tool}"}

            return {
                "tool": query.tool,
                "query": query.query,
                "purpose": query.purpose,
                "result": result,
            }
        except Exception as exc:
            logger.exception("Query execution failed: %s %s", query.tool, query.query)
            return {
                "tool": query.tool,
                "query": query.query,
                "purpose": query.purpose,
                "error": str(exc),
            }

    async def execute_hypothesis_queries(
        self, hypothesis: Hypothesis, alert_time: datetime
    ) -> list[dict]:
        """Execute all queries for a hypothesis and return the evidence."""
        evidence = []
        for query in hypothesis.queries:
            result = await self.execute_query(query, alert_time)
            result["hypothesis_id"] = hypothesis.id
            evidence.append(result)

        logger.info(
            "Executed %d queries for hypothesis '%s'",
            len(evidence),
            hypothesis.title,
        )
        return evidence

    async def execute_all(
        self, hypotheses: list[Hypothesis], alert_time: datetime
    ) -> list[dict]:
        """Execute queries for all pending hypotheses."""
        all_evidence = []
        for h in hypotheses:
            if h.status.value in ("pending", "investigating"):
                results = await self.execute_hypothesis_queries(h, alert_time)
                all_evidence.extend(results)
        return all_evidence
