"""Alert webhook receiver — accepts Alertmanager and manual triggers."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from agent.ingestion.models import AlertmanagerPayload, NormalizedAlert
from agent.ingestion.normalizer import normalize_payload
from agent.queue.producer import enqueue_alert

logger = logging.getLogger("agent.ingestion")
router = APIRouter(prefix="/alerts", tags=["ingestion"])


@router.post("/webhook")
async def alertmanager_webhook(payload: AlertmanagerPayload):
    """Receive Alertmanager webhook, dedup, and enqueue for investigation."""
    alerts = normalize_payload(payload)
    firing = [a for a in alerts if a.status.value == "firing"]

    logger.info("Received %d alerts (%d firing)", len(alerts), len(firing))

    enqueued = []
    deduplicated = []
    for alert in firing:
        msg_id = await enqueue_alert(alert)
        if msg_id:
            enqueued.append(alert.id)
        else:
            deduplicated.append(alert.id)

    return {
        "received": len(alerts),
        "firing": len(firing),
        "enqueued": enqueued,
        "deduplicated": deduplicated,
    }


@router.post("/manual")
async def manual_trigger(alert: NormalizedAlert):
    """Manually trigger an investigation with a crafted alert (bypasses dedup)."""
    from agent.queue.redis_client import STREAM_KEY, get_redis

    r = await get_redis()
    msg_id = await r.xadd(STREAM_KEY, {"alert_json": alert.model_dump_json()})
    logger.info("Manual investigation enqueued: alert=%s name=%s msg=%s", alert.id, alert.name, msg_id)

    return {"investigation_enqueued": alert.id, "alert_name": alert.name, "stream_msg": msg_id}
