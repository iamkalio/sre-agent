"""Structured JSON logging with trace context."""

import logging
import sys

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from app.telemetry.tracing import SERVICE_NAME, SERVICE_VERSION

_JSON_FORMAT = (
    '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
    '"logger":"%(name)s","message":"%(message)s",'
    '"trace_id":"%(otelTraceID)s","span_id":"%(otelSpanID)s",'
    '"service":"%(otelServiceName)s"}'
)

_UVICORN_FORMAT = (
    '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
    '"logger":"%(name)s","message":"%(message)s"}'
)

_OTEL_DEFAULTS = {
    "otelTraceID": "0",
    "otelSpanID": "0",
    "otelServiceName": SERVICE_NAME,
}


class _SafeOtelFormatter(logging.Formatter):
    """Formatter that injects OTEL fields with safe defaults for non-instrumented loggers."""

    def format(self, record: logging.LogRecord) -> str:
        for key, default in _OTEL_DEFAULTS.items():
            if not hasattr(record, key):
                setattr(record, key, default)
        return super().format(record)


def setup_logging(
    otlp_endpoint: str = "http://otel-collector:4317",
    level: int = logging.INFO,
) -> logging.Logger:
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
        }
    )

    log_provider = LoggerProvider(resource=resource)
    otlp_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

    otel_handler = LoggingHandler(level=level, logger_provider=log_provider)

    json_formatter = _SafeOtelFormatter(_JSON_FORMAT)
    uvicorn_formatter = logging.Formatter(_UVICORN_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(json_formatter)

    uvicorn_handler = logging.StreamHandler(sys.stdout)
    uvicorn_handler.setFormatter(uvicorn_formatter)

    logger = logging.getLogger("sre_playground")
    logger.setLevel(level)
    logger.addHandler(stream_handler)
    logger.addHandler(otel_handler)

    logging.getLogger("uvicorn.access").handlers = [uvicorn_handler]
    logging.getLogger("uvicorn.error").handlers = [uvicorn_handler]

    return logger
