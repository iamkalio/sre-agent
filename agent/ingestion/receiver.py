"""Alert webhook receiver — accepts Alertmanager and manual triggers."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks

from agent.ingestion.models import AlertmanagerPayload, NormalizedAlert
from agent.ingestion.normalizer import normalize_payload

logger = logging.getLogger("agent.ingestion")
router = APIRouter(prefix="/alerts", tags=["ingestion"])

_investigation_callback = None


def register_investigation_callback(fn):
    """Register the function to call when a new alert arrives."""
    global _investigation_callback
    _investigation_callback = fn


@router.post("/webhook")
async def alertmanager_webhook(payload: AlertmanagerPayload, background_tasks: BackgroundTasks):
    """Receive Alertmanager webhook and kick off investigations."""
    alerts = normalize_payload(payload)
    firing = [a for a in alerts if a.status.value == "firing"]

    logger.info("Received %d alerts (%d firing)", len(alerts), len(firing))

    started = []
    for alert in firing:
        if _investigation_callback:
            background_tasks.add_task(_investigation_callback, alert)
            started.append(alert.id)
            logger.info("Investigation queued for alert=%s name=%s", alert.id, alert.name)

    return {
        "received": len(alerts),
        "firing": len(firing),
        "investigations_started": started,
    }


@router.post("/manual")
async def manual_trigger(alert: NormalizedAlert, background_tasks: BackgroundTasks):
    """Manually trigger an investigation with a crafted alert."""
    if _investigation_callback:
        background_tasks.add_task(_investigation_callback, alert)
        logger.info("Manual investigation queued for alert=%s name=%s", alert.id, alert.name)

    return {"investigation_started": alert.id, "alert_name": alert.name}
