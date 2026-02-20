"""Normalize diverse alert formats into a canonical NormalizedAlert."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from agent.ingestion.models import (
    AlertSeverity,
    AlertStatus,
    AlertmanagerPayload,
    NormalizedAlert,
    RawAlert,
)

logger = logging.getLogger("agent.ingestion")

_SEVERITY_MAP = {
    "critical": AlertSeverity.CRITICAL,
    "warning": AlertSeverity.WARNING,
    "info": AlertSeverity.INFO,
}


def _parse_ts(raw: str) -> datetime:
    if not raw or raw == "0001-01-01T00:00:00Z":
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def normalize_raw_alert(raw: RawAlert) -> NormalizedAlert:
    severity_str = raw.labels.get("severity", "warning").lower()
    return NormalizedAlert(
        name=raw.labels.get("alertname", "unknown"),
        severity=_SEVERITY_MAP.get(severity_str, AlertSeverity.WARNING),
        status=AlertStatus.FIRING if raw.status == "firing" else AlertStatus.RESOLVED,
        summary=raw.annotations.get("summary", ""),
        description=raw.annotations.get("description", ""),
        labels=raw.labels,
        starts_at=_parse_ts(raw.starts_at),
        ends_at=_parse_ts(raw.ends_at) if raw.ends_at else None,
        generator_url=raw.generator_url,
        fingerprint=raw.fingerprint,
        raw=raw.model_dump(),
    )


def normalize_payload(payload: AlertmanagerPayload) -> list[NormalizedAlert]:
    """Normalize an entire Alertmanager webhook into a list of alerts."""
    alerts = []
    for raw_alert in payload.alerts:
        try:
            alerts.append(normalize_raw_alert(raw_alert))
        except Exception:
            logger.exception("Failed to normalize alert: %s", raw_alert.labels)
    return alerts
