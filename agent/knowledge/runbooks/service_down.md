# Runbook: Service Down

## Alert
`ServiceDown` — fires when `up{job="sre-playground"} == 0` for 30 seconds

## Possible Causes

1. **Container crash** — OOM kill, unhandled exception, or segfault
2. **Deployment in progress** — rolling update with brief unavailability
3. **Resource limits** — container killed by orchestrator for exceeding limits
4. **Dependency failure** — crash-loop due to missing dependency (database, config)
5. **Network issue** — Prometheus can't reach the app (DNS, network partition)

## Investigation Steps

1. Check if the container is running:
   - Look at Docker/Kubernetes container status
2. Check container logs for crash reason:
   - `{service_name="sre-playground"} | json` — look for final log entries
3. Check if it's a scrape issue vs actual downtime:
   - Can other services reach the app?
   - `up{job="sre-playground"}` — scrape success metric
4. Check for resource limit violations:
   - `process_resident_memory_bytes` — was memory climbing before crash?
   - CPU throttling?
5. Check if a deployment was happening:
   - Recent image changes, config updates

## Common Resolutions

- **OOM kill**: Increase memory limits, fix memory leak
- **Unhandled exception**: Check logs for stack trace, deploy fix
- **Dependency failure**: Restore the dependency, add health checks
- **Network issue**: Check DNS, security groups, network policies
- **Deployment**: Wait for rollout to complete, rollback if stuck

## Key Metrics

- `up{job="sre-playground"}` — scrape success (1=up, 0=down)
- `process_resident_memory_bytes` — memory before crash
- `http_requests_total` — request rate (drops to 0 when down)
