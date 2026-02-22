"""Alert producer — dedup + enqueue normalized alerts into Redis Stream."""

from __future__ import annotations

import json
import logging

from agent.config import settings
from agent.ingestion.models import NormalizedAlert
from agent.queue.redis_client import DEDUP_PREFIX, STREAM_KEY, get_redis

logger = logging.getLogger("agent.queue")


async def enqueue_alert(alert: NormalizedAlert) -> str | None:
    """Deduplicate and push an alert onto the Redis stream.

    Returns the stream message ID if enqueued, None if deduplicated.
    """
    r = await get_redis()

    dedup_key = f"{DEDUP_PREFIX}{alert.fingerprint or alert.name}"
    already_seen = await r.set(
        dedup_key, "1",
        nx=True,
        ex=settings.dedup_window_seconds,
    )

    if not already_seen:
        logger.info(
            "Alert deduplicated (seen within %ds): name=%s fingerprint=%s",
            settings.dedup_window_seconds, alert.name, alert.fingerprint,
        )
        return None

    msg_id = await r.xadd(STREAM_KEY, {
        "alert_json": alert.model_dump_json(),
    })

    logger.info("Alert enqueued: name=%s id=%s stream_msg=%s", alert.name, alert.id, msg_id)
    return msg_id
