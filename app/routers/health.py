"""Health and work endpoints."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from opentelemetry import trace

router = APIRouter()
logger = logging.getLogger("sre_playground")
tracer = trace.get_tracer(__name__)

_start_time = datetime.now(timezone.utc)


@router.get("/health")
async def health():
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/work")
async def work():
    with tracer.start_as_current_span("do-work") as span:
        span.set_attribute("work.type", "normal")
        logger.info("Processing work request")
        await asyncio.sleep(0.05 + 0.1 * (time.time() % 1))
        span.set_attribute("work.result", "success")
        return {"status": "completed", "duration_ms": round((time.time() % 1) * 100, 2)}
