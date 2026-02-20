# Runbook: High Request Latency

## Alert
`HighRequestLatency` — fires when p95 latency exceeds 2 seconds for 2 minutes

## Possible Causes

1. **Latency simulation** — the `/simulate/latency` endpoint was triggered
2. **Downstream dependency slowness** — database, API, or network latency
3. **Resource contention** — CPU or I/O saturation causing request queuing
4. **Connection pool exhaustion** — requests waiting for available connections
5. **Large payload processing** — unexpectedly large request/response bodies

## Investigation Steps

1. Check if latency simulation is active:
   - `active_simulations{simulation_type="latency"}` — should be > 0 during simulation
2. Identify which endpoints are slow:
   - `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (endpoint)`
3. Check if latency is uniform or endpoint-specific:
   - Uniform: infrastructure issue (CPU, network, memory)
   - Endpoint-specific: code or dependency issue
4. Pull traces for slow requests:
   - Search Tempo for traces with duration > 2s
   - Examine span waterfall to find the slow component
5. Check for correlated CPU or memory pressure:
   - `cpu_spike_total`, `app_memory_usage_bytes`
6. Review error logs for timeout messages:
   - `{service_name="sre-playground"} |= "timeout" | json`

## Common Resolutions

- **Simulation**: No action — `/simulate/latency` adds artificial delay
- **Dependency slowness**: Check dependency health, add circuit breaker
- **Resource contention**: Scale up/out, optimize hot paths
- **Connection pool**: Increase pool size, add connection timeout

## Key Metrics

- `http_request_duration_seconds` — histogram of request durations
- `active_simulations{simulation_type="latency"}` — active latency simulations
- `http_requests_total` — check for correlated request volume changes
