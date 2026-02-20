# Runbook: High CPU / CPU Spike

## Alert
`HighCPUSpikes` — fires when `rate(cpu_spike_total[5m]) > 0.1`

## Possible Causes

1. **Chaos simulation** — the `/simulate/cpu` endpoint was triggered, burning CPU for N seconds
2. **Runaway computation** — infinite loop, expensive regex, or algorithmic blowup
3. **Traffic spike** — sudden increase in request volume overwhelming workers
4. **Memory pressure** — excessive garbage collection consuming CPU
5. **Crypto/compression** — TLS handshakes or payload compression under load

## Investigation Steps

1. Check if a CPU simulation was triggered:
   - `cpu_spike_total` — counter should increment when simulations run
   - `active_simulations{simulation_type="cpu"}` — shows active simulations
2. Check request rate for traffic spikes:
   - `rate(http_requests_total[5m])`
3. Pull logs around the CPU spike:
   - `{service_name="sre-playground"} |= "CPU spike" | json`
4. Check memory pressure:
   - `app_memory_usage_bytes` — correlated memory spikes suggest GC pressure
5. Look at trace durations for slow requests:
   - Search Tempo for spans with high duration

## Common Resolutions

- **Simulation**: No action — intentional chaos testing
- **Runaway process**: Identify and kill the process, deploy fix
- **Traffic spike**: Scale horizontally, enable rate limiting
- **GC pressure**: Increase memory limits, optimize allocations

## Key Metrics

- `cpu_spike_total` — simulation counter
- `active_simulations{simulation_type="cpu"}` — currently running
- `process_cpu_seconds_total` — actual process CPU usage
- `http_requests_total` — request volume
