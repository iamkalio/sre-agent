"""Prometheus metrics endpoint."""

from fastapi import APIRouter
from starlette.responses import Response

from app.telemetry.metrics import get_metrics

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics():
    body, content_type = get_metrics()
    return Response(content=body, media_type=content_type)
