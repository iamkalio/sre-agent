"""SRE Playground — FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.middleware import MetricsMiddleware
from app.routers import health, metrics, simulate
from app.telemetry.logging import setup_logging
from app.telemetry.tracing import setup_tracing

OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

setup_tracing(otlp_endpoint=OTLP_ENDPOINT)
logger = setup_logging(otlp_endpoint=OTLP_ENDPOINT)

app = FastAPI(
    title="SRE Playground",
    description="A Docker-based SRE observability playground",
    version="1.0.0",
)

app.add_middleware(MetricsMiddleware)

app.include_router(health.router)
app.include_router(simulate.router)
app.include_router(metrics.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


FastAPIInstrumentor.instrument_app(app)

logger.info("SRE Playground started")
