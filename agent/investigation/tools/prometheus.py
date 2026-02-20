"""Prometheus query tool — executes PromQL against the Prometheus HTTP API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from agent.config import settings

logger = logging.getLogger("agent.investigation.tools")


class PrometheusClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.prometheus_url,
            timeout=15.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def instant_query(self, promql: str, time: datetime | None = None) -> dict:
        """Execute a PromQL instant query."""
        params: dict = {"query": promql}
        if time:
            params["time"] = time.timestamp()

        resp = await self._http.get("/api/v1/query", params=params)
        body = resp.json()

        if body.get("status") != "success":
            logger.warning("PromQL query failed: %s — %s", promql, body.get("error"))
            return {"query": promql, "status": "error", "error": body.get("error"), "result": []}

        return {
            "query": promql,
            "status": "success",
            "result_type": body["data"]["resultType"],
            "result": body["data"]["result"],
        }

    async def range_query(
        self,
        promql: str,
        start: datetime | None = None,
        end: datetime | None = None,
        step: str = "15s",
    ) -> dict:
        """Execute a PromQL range query."""
        now = datetime.now(timezone.utc)
        start = start or now - timedelta(minutes=settings.query_lookback_minutes)
        end = end or now

        resp = await self._http.get("/api/v1/query_range", params={
            "query": promql,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        })
        body = resp.json()

        if body.get("status") != "success":
            logger.warning("PromQL range query failed: %s — %s", promql, body.get("error"))
            return {"query": promql, "status": "error", "error": body.get("error"), "result": []}

        return {
            "query": promql,
            "status": "success",
            "result_type": body["data"]["resultType"],
            "result": body["data"]["result"],
        }

    async def get_alerts(self) -> list[dict]:
        """Fetch currently firing alerts from Prometheus."""
        resp = await self._http.get("/api/v1/alerts")
        body = resp.json()
        return body.get("data", {}).get("alerts", [])
