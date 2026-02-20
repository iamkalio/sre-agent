"""Chaos simulation endpoints for SRE testing."""

import asyncio
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks
from opentelemetry import trace

from app.telemetry.metrics import (
    active_simulations,
    cpu_spike_counter,
    error_counter,
    memory_usage_gauge,
)

router = APIRouter(prefix="/simulate", tags=["simulations"])
logger = logging.getLogger("sre_playground")
tracer = trace.get_tracer(__name__)
_executor = ThreadPoolExecutor(max_workers=4)


def _cpu_burn(duration_seconds: int = 30) -> None:
    """Burn CPU in a background thread."""
    active_simulations.labels(simulation_type="cpu").inc()
    logger.warning("CPU spike started for %d seconds", duration_seconds)
    end = time.monotonic() + duration_seconds
    while time.monotonic() < end:
        math.factorial(5000)
    active_simulations.labels(simulation_type="cpu").dec()
    logger.info("CPU spike ended")


def _memory_allocate(mb: int = 256, hold_seconds: int = 30) -> None:
    """Allocate memory temporarily."""
    active_simulations.labels(simulation_type="memory").inc()
    logger.warning("Memory spike started: allocating %d MB for %d seconds", mb, hold_seconds)
    blocks = [bytearray(1024 * 1024) for _ in range(mb)]  # noqa: F841
    memory_usage_gauge.set(mb * 1024 * 1024)
    time.sleep(hold_seconds)
    del blocks
    memory_usage_gauge.set(0)
    active_simulations.labels(simulation_type="memory").dec()
    logger.info("Memory spike ended, %d MB released", mb)


@router.post("/cpu")
async def simulate_cpu(background_tasks: BackgroundTasks, duration: int = 30):
    with tracer.start_as_current_span("simulate-cpu") as span:
        span.set_attribute("simulation.type", "cpu")
        span.set_attribute("simulation.duration_seconds", duration)
        cpu_spike_counter.inc()
        _executor.submit(_cpu_burn, duration)
        logger.warning("CPU spike simulation triggered for %d seconds", duration)
        return {
            "simulation": "cpu_spike",
            "duration_seconds": duration,
            "status": "started",
        }


@router.post("/error")
async def simulate_error(count: int = 50):
    with tracer.start_as_current_span("simulate-errors") as span:
        span.set_attribute("simulation.type", "error_burst")
        span.set_attribute("simulation.error_count", count)
        active_simulations.labels(simulation_type="error").inc()
        for i in range(count):
            error_counter.labels(error_type="simulated_500").inc()
            logger.error("Simulated error %d/%d: Internal Server Error", i + 1, count)
        active_simulations.labels(simulation_type="error").dec()
        return {
            "simulation": "error_burst",
            "errors_generated": count,
            "status": "completed",
        }


@router.post("/latency")
async def simulate_latency(delay: float = 3.0):
    with tracer.start_as_current_span("simulate-latency") as span:
        span.set_attribute("simulation.type", "latency")
        span.set_attribute("simulation.delay_seconds", delay)
        active_simulations.labels(simulation_type="latency").inc()
        logger.warning("Latency simulation: sleeping %.1f seconds", delay)
        await asyncio.sleep(delay)
        active_simulations.labels(simulation_type="latency").dec()
        return {
            "simulation": "latency_injection",
            "delay_seconds": delay,
            "status": "completed",
        }


@router.post("/memory")
async def simulate_memory(
    background_tasks: BackgroundTasks,
    mb: int = 256,
    hold_seconds: int = 30,
):
    with tracer.start_as_current_span("simulate-memory") as span:
        span.set_attribute("simulation.type", "memory")
        span.set_attribute("simulation.mb", mb)
        span.set_attribute("simulation.hold_seconds", hold_seconds)
        _executor.submit(_memory_allocate, mb, hold_seconds)
        logger.warning("Memory spike simulation triggered: %d MB for %d seconds", mb, hold_seconds)
        return {
            "simulation": "memory_spike",
            "allocated_mb": mb,
            "hold_seconds": hold_seconds,
            "status": "started",
        }
