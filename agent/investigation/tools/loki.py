"""Loki query tool — executes LogQL against the Loki HTTP API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from agent.config import settings

logger = logging.getLogger("agent.investigation.tools")


class LokiClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.loki_url,
            timeout=15.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def query_range(
        self,
        logql: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> dict:
        """Execute a LogQL range query."""
        now = datetime.now(timezone.utc)
        start = start or now - timedelta(minutes=settings.query_lookback_minutes)
        end = end or now

        resp = await self._http.get("/loki/api/v1/query_range", params={
            "query": logql,
            "start": str(int(start.timestamp())),
            "end": str(int(end.timestamp())),
            "limit": limit,
        })
        body = resp.json()

        streams = body.get("data", {}).get("result", [])
        log_lines = []
        for stream in streams:
            for ts, line in stream.get("values", []):
                log_lines.append({"timestamp": ts, "line": line, "labels": stream.get("stream", {})})

        return {
            "query": logql,
            "status": "success",
            "streams": len(streams),
            "total_lines": len(log_lines),
            "lines": log_lines[:limit],
        }

    async def query_instant(self, logql: str) -> dict:
        """Execute a LogQL instant query (useful for metric-style log queries)."""
        resp = await self._http.get("/loki/api/v1/query", params={"query": logql})
        body = resp.json()
        return {
            "query": logql,
            "status": "success",
            "result": body.get("data", {}).get("result", []),
        }
