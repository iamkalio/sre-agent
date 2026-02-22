"""Investigation worker — pulls alerts from Redis Stream with concurrency control."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from agent.config import settings
from agent.ingestion.models import NormalizedAlert
from agent.queue.redis_client import CONSUMER_GROUP, STREAM_KEY, get_redis

logger = logging.getLogger("agent.queue.worker")

CONSUMER_NAME = "worker-1"


class InvestigationWorker:
    """Consumes alerts from Redis Stream and runs investigations with bounded concurrency."""

    def __init__(self, investigate_fn: Callable[[NormalizedAlert], Awaitable[None]]) -> None:
        self._investigate = investigate_fn
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_investigations)
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        r = await get_redis()
        try:
            await r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
            logger.info("Created consumer group '%s' on stream '%s'", CONSUMER_GROUP, STREAM_KEY)
        except Exception:
            pass  # group already exists

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "Worker started: max_concurrent=%d, timeout=%ds",
            settings.max_concurrent_investigations,
            settings.investigation_timeout_seconds,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Worker stopped")

    async def _poll_loop(self) -> None:
        """Main loop: read from stream, dispatch with concurrency limit."""
        r = await get_redis()

        while self._running:
            try:
                messages = await r.xreadgroup(
                    CONSUMER_GROUP, CONSUMER_NAME,
                    {STREAM_KEY: ">"},
                    count=1,
                    block=2000,
                )

                if not messages:
                    continue

                for _stream, entries in messages:
                    for msg_id, data in entries:
                        alert_json = data.get("alert_json", "")
                        if not alert_json:
                            await r.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                            continue

                        alert = NormalizedAlert.model_validate_json(alert_json)
                        asyncio.create_task(
                            self._run_with_guard(alert, msg_id)
                        )

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Worker poll error — retrying in 5s")
                await asyncio.sleep(5)

    async def _run_with_guard(self, alert: NormalizedAlert, msg_id: str) -> None:
        """Run an investigation with semaphore + timeout, then ACK."""
        async with self._semaphore:
            logger.info(
                "Investigation starting: alert=%s name=%s (msg=%s)",
                alert.id, alert.name, msg_id,
            )
            try:
                await asyncio.wait_for(
                    self._investigate(alert),
                    timeout=settings.investigation_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Investigation timed out after %ds: alert=%s name=%s",
                    settings.investigation_timeout_seconds, alert.id, alert.name,
                )
            except Exception:
                logger.exception("Investigation failed: alert=%s", alert.id)
            finally:
                r = await get_redis()
                await r.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                logger.info("Message acknowledged: %s", msg_id)
