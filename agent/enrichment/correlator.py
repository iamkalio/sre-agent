"""Cross-signal correlation — tie metrics anomalies to log patterns and traces."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from agent.config import settings

logger = logging.getLogger("agent.enrichment")


class SignalCorrelator:
    """Pulls a snapshot from each backend around an alert window and finds connections."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def get_metrics_snapshot(
        self, queries: list[str], center: datetime, window_minutes: int = 15
    ) -> dict[str, list]:
        """Run a batch of PromQL instant queries around the alert time."""
        results: dict[str, list] = {}
        ts = center.timestamp()
        for q in queries:
            try:
                resp = await self._http.get(
                    f"{settings.prometheus_url}/api/v1/query",
                    params={"query": q, "time": ts},
                )
                data = resp.json()
                results[q] = data.get("data", {}).get("result", [])
            except Exception:
                logger.exception("Prometheus query failed: %s", q)
                results[q] = []
        return results

    async def get_recent_errors(self, center: datetime, window_minutes: int = 15) -> list[dict]:
        """Pull error-level logs from Loki around the alert time."""
        start = center - timedelta(minutes=window_minutes)
        end = center + timedelta(minutes=window_minutes // 3)
        logql = '{service_name="sre-playground"} |= "error" | json'
        try:
            resp = await self._http.get(
                f"{settings.loki_url}/loki/api/v1/query_range",
                params={
                    "query": logql,
                    "start": int(start.timestamp()),
                    "end": int(end.timestamp()),
                    "limit": 50,
                },
            )
            data = resp.json()
            return data.get("data", {}).get("result", [])
        except Exception:
            logger.exception("Loki error log query failed")
            return []

    async def get_error_traces(self, center: datetime, window_minutes: int = 15) -> list[dict]:
        """Search Tempo for error traces around the alert time."""
        start = center - timedelta(minutes=window_minutes)
        end = center + timedelta(minutes=window_minutes // 3)
        try:
            resp = await self._http.get(
                f"{settings.tempo_url}/api/search",
                params={
                    "start": int(start.timestamp()),
                    "end": int(end.timestamp()),
                    "limit": 20,
                },
            )
            data = resp.json()
            return data.get("traces", [])
        except Exception:
            logger.exception("Tempo trace search failed")
            return []

    async def correlate(self, alert_name: str, alert_time: datetime) -> dict:
        """Build a correlation snapshot for an alert."""
        default_queries = [
            "sum(rate(app_errors_total[5m])) by (error_type)",
            "sum(rate(http_requests_total[5m])) by (status_code)",
            "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
            "cpu_spike_total",
            "app_memory_usage_bytes",
            "active_simulations",
        ]

        metrics, errors, traces = await asyncio.gather(
            self.get_metrics_snapshot(default_queries, alert_time),
            self.get_recent_errors(alert_time),
            self.get_error_traces(alert_time),
        )

        return {
            "alert_name": alert_name,
            "alert_time": alert_time.isoformat(),
            "metrics": metrics,
            "error_logs_count": sum(len(r.get("values", [])) for r in errors),
            "error_logs_sample": errors[:5],
            "traces_found": len(traces),
            "traces_sample": traces[:5],
        }
