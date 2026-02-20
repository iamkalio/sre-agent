# Runbook: High Memory Usage

## Alert
`HighMemoryUsage` — fires when `app_memory_usage_bytes > 200MB` for 1 minute

## Possible Causes

1. **Memory simulation** — the `/simulate/memory` endpoint was triggered
2. **Memory leak** — objects accumulating without being freed
3. **Cache blowup** — unbounded in-memory cache growing without eviction
4. **Large request processing** — file uploads, batch operations, or report generation
5. **Connection accumulation** — leaked connections holding memory

## Investigation Steps

1. Check if memory simulation is active:
   - `active_simulations{simulation_type="memory"}` — should be > 0 during simulation
   - `app_memory_usage_bytes` — shows allocated memory amount
2. Check the memory allocation timeline:
   - Was it a sudden spike (simulation/single event) or gradual increase (leak)?
3. Pull logs around the memory spike:
   - `{service_name="sre-playground"} |= "memory" | json`
4. Check for correlated errors:
   - Memory pressure can cause OOM kills and cascading errors
   - `rate(app_errors_total[5m])`
5. Look for correlated CPU spikes:
   - Memory pressure triggers GC which burns CPU
   - `cpu_spike_total`

## Common Resolutions

- **Simulation**: No action — memory is released automatically after the hold period
- **Memory leak**: Identify the leak with profiling, deploy fix, restart as mitigation
- **Cache blowup**: Add eviction policy (LRU, TTL), set max cache size
- **Large requests**: Add request size limits, stream large payloads
- **Connection leak**: Fix connection handling, set connection timeouts

## Key Metrics

- `app_memory_usage_bytes` — application-reported memory allocation
- `active_simulations{simulation_type="memory"}` — active memory simulations
- `process_resident_memory_bytes` — actual process RSS
- `process_virtual_memory_bytes` — virtual memory size

## Notes

Memory simulations in this playground allocate N MB of bytearrays for a configurable
duration, then release them. The `app_memory_usage_bytes` gauge resets to 0 after release.
If the gauge stays elevated after the hold period, it may indicate a real issue.
