"""Prometheus metrics definitions."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    labelnames=["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

error_counter = Counter(
    "app_errors_total",
    "Total application errors",
    labelnames=["error_type"],
)

cpu_spike_counter = Counter(
    "cpu_spike_total",
    "Number of CPU spike simulations triggered",
)

memory_usage_gauge = Gauge(
    "app_memory_usage_bytes",
    "Current application memory usage in bytes",
)

active_simulations = Gauge(
    "active_simulations",
    "Number of currently active simulations",
    labelnames=["simulation_type"],
)


def get_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
