"""Tempo query tool — searches and retrieves traces via the Tempo HTTP API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from agent.config import settings

logger = logging.getLogger("agent.investigation.tools")


class TempoClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.tempo_url,
            timeout=15.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def search(
        self,
        tags: str = "",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Search for traces matching tags within a time window."""
        now = datetime.now(timezone.utc)
        start = start or now - timedelta(minutes=settings.query_lookback_minutes)
        end = end or now

        params: dict = {
            "start": str(int(start.timestamp())),
            "end": str(int(end.timestamp())),
            "limit": limit,
        }
        if tags:
            params["tags"] = tags

        resp = await self._http.get("/api/search", params=params)
        body = resp.json()

        traces = body.get("traces", [])
        return {
            "status": "success",
            "traces_found": len(traces),
            "traces": traces,
        }

    async def get_trace(self, trace_id: str) -> dict:
        """Retrieve the full span tree for a specific trace."""
        resp = await self._http.get(f"/api/traces/{trace_id}")
        if resp.status_code != 200:
            return {"trace_id": trace_id, "status": "not_found"}

        body = resp.json()
        batches = body.get("batches", [])
        spans = []
        for batch in batches:
            for scope_spans in batch.get("scopeSpans", batch.get("instrumentationLibrarySpans", [])):
                for span in scope_spans.get("spans", []):
                    spans.append({
                        "name": span.get("name"),
                        "kind": span.get("kind"),
                        "status": span.get("status", {}),
                        "duration_ns": int(span.get("endTimeUnixNano", 0)) - int(span.get("startTimeUnixNano", 0)),
                        "attributes": {
                            a["key"]: a.get("value", {})
                            for a in span.get("attributes", [])
                        },
                    })

        return {
            "trace_id": trace_id,
            "status": "success",
            "span_count": len(spans),
            "spans": spans,
        }
