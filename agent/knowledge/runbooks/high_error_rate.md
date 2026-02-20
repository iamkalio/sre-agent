# Runbook: High Error Rate

## Alert
`HighErrorRate` — fires when `rate(app_errors_total[5m]) > 1`

## Possible Causes

1. **Bad deployment** — a recent code change introduced a bug generating 5xx errors
2. **Downstream dependency failure** — an upstream API or database is unreachable
3. **Resource exhaustion** — connection pool, file descriptors, or memory limits hit
4. **Configuration change** — misconfigured feature flag, environment variable, or secret rotation
5. **Chaos simulation** — the `/simulate/error` endpoint was triggered intentionally

## Investigation Steps

1. Identify which `error_type` label is dominant:
   - `rate(app_errors_total[5m]) by (error_type)`
2. Check if errors correlate with a specific endpoint:
   - `rate(http_requests_total{status_code=~"5.."}[5m]) by (endpoint)`
3. Pull error logs around the alert start time:
   - `{service_name="sre-playground"} |= "error" | json`
4. Search for error traces:
   - Look for spans with error status in Tempo
5. Check if a deployment or config change happened recently
6. Verify downstream service health

## Common Resolutions

- **Simulated errors**: No action needed — `/simulate/error` generates synthetic errors
- **Bad deployment**: Roll back to the previous version
- **Dependency failure**: Check downstream service health, failover if available
- **Resource exhaustion**: Increase limits, restart affected pods
- **Config error**: Revert the configuration change

## Key Metrics

- `app_errors_total` — total error counter by type
- `http_requests_total` — request counter by status code
- `http_request_duration_seconds` — latency (errors may increase latency)
