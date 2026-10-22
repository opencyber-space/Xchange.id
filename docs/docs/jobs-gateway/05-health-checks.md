[← Back to index](README.md)

# 5. Health checks

Implemented by `HealthChecker` (`jobs-gateway/core/health.py`) on top of
`ExchangeClient.check_health()` (`jobs-gateway/core/exchange_client.py`).

## 5.1 The probe

exchange-db has no dedicated health endpoint, so the gateway probes it with
a request any exchange-db instance can answer:

```
GET {exchange_api_url}/tasks/__jobs_gateway_health_probe__
```

No task can have that ID, so a working exchange-db runs a real MongoDB lookup
and replies `404 {"ok": false, "error": "task not found"}`. The probe counts
as **healthy** if the response:

- has status `200` or `404`, **and**
- has a JSON object body containing an `"ok"` key, i.e. the exchange-db
  envelope.

Getting that envelope back shows both that the exchange's Flask app is
serving and that its MongoDB connection works. A `404` with an HTML body
(wrong host or path, some other service on that port), a `5xx` (exchange up
but Mongo down), a timeout or a connection error all count as
**unreachable**.

The probe uses a `(5, 10)` second `(connect, read)` timeout.

## 5.2 When probes run

| Trigger | Effect on failure |
|---|---|
| `POST /exchanges` (registration), unless `skip_health_check: true` | Registration is rejected with `400`. Nothing is stored. |
| `POST /exchanges/{id}/health-check` (manual) | Entry updated to `unreachable`. The response is still `200`. |
| Background sweep every `HEALTH_CHECK_INTERVAL` seconds | Entry updated to `unreachable`. |

**Background sweep.** `run_server()` starts one daemon thread that loops
forever: probe every registered exchange **sequentially**, then sleep
`HEALTH_CHECK_INTERVAL` seconds (default `30`). A sweep therefore takes up
to about 15 s per unresponsive exchange, which pushes the next sweep back by
the same amount. Set `HEALTH_CHECK_INTERVAL=0` to disable the sweep entirely,
leaving only registration-time and manual checks. An error in one sweep (for
example the gateway's own MongoDB being briefly unavailable) is logged and
the loop carries on.

## 5.3 What gets written

Each probe, whatever triggered it, writes three server-managed fields onto
the registry entry:

| Probe result | `exchange_status` | `last_health_check_error` | `last_health_check_time` |
|---|---|---|---|
| success | `healthy` | `""` | now (UTC) |
| failure | `unreachable` | the exception message | now (UTC) |

`exchange_status` reads `unknown` only between a registration with
`skip_health_check: true`, or an `exchange_api_url` change, and the next
probe. See [§1.3](01-concepts.md#13-exchange-status).

## 5.4 What status does and does not affect

- **Discovery:** only if you ask. Pass `"status": "healthy"` to `/discover`
  to skip exchanges that failed their last probe
  ([§4.2](04-discovery.md#42-stage-1-registry-filter)).
- **Forwarding:** never. `/exchanges/{id}/api/...` always attempts the call
  ([§3.3](03-apis.md#33-gateway-forwarding)).
- **Registry membership:** never. An exchange that stays `unreachable` is
  not removed automatically. Remove it with `DELETE /exchanges/{id}` if it
  has been decommissioned. To list candidates for cleanup:
  `POST /exchanges/query {"exchange_status": "unreachable"}`.

A healthy probe says nothing about the exchange's own downstream
dependencies (function registry, delegate system, Orcade). Those only fail
at task-processing time and show up as `failed` tasks on the exchange.

---
[← Previous: Discovery](04-discovery.md) · [Back to index](README.md) · [Next: Deployment & walkthrough →](06-deployment.md)
