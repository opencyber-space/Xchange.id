[← Back to index](README.md)

# 3. APIs

Base path: none (routes are mounted at root). Default port `5000`, which
can be overridden with the `PORT` env var (unlike exchange-db, where `PORT`
is informational only).

## 3.1 Response envelope

The gateway's own endpoints use the same envelope as exchange-db and Orcade:

```json
// success
{ "ok": true, "data": { ... } }

// failure
{ "ok": false, "error": "human readable message" }
```

Forwarded calls ([§3.3](#33-gateway-forwarding)) return **the exchange's**
response body and status code unchanged. Since exchange-db uses the same
envelope, callers can't tell the two apart, except for the gateway's own
`404` / `502` errors described there.

## 3.2 Registry

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/exchanges` | Register an exchange |
| `GET` | `/exchanges/{exchange_id}` | Fetch one registry entry |
| `PUT` / `PATCH` | `/exchanges/{exchange_id}` | Raw `$set` update; returns the fresh entry |
| `DELETE` | `/exchanges/{exchange_id}` | Remove an exchange from the registry |
| `POST` | `/exchanges/query` | Query registry entries with a raw Mongo filter |
| `POST` | `/exchanges/{exchange_id}/health-check` | Probe the exchange now and return the updated entry |

### Register

`POST /exchanges`

**Request body:**

| Field | Type | Default if omitted |
|---|---|---|
| `exchange_id` | string | **required**. `400` if missing |
| `exchange_api_url` | string | **required**. `400` if missing |
| `exchange_name` | string | `""` |
| `exchange_description` | string | `""` |
| `exchange_tags` | array&lt;string&gt; | `[]` |
| `exchange_metadata` | object | `{}` |
| `skip_health_check` | boolean | `false`. When `true`, register without probing (status starts as `unknown`) |

Unless `skip_health_check` is `true`, the gateway probes the exchange first
([§5.1](05-health-checks.md#51-the-probe)) and refuses to register it if the
probe fails. This catches typos in `exchange_api_url` at registration time
rather than at first use.

```bash
curl -X POST http://localhost:5000/exchanges \
  -H "Content-Type: application/json" \
  -d '{
    "exchange_id": "demo-exchange",
    "exchange_api_url": "http://demo-exchange-svc.exchanges.svc.cluster.local:5000",
    "exchange_name": "Demo exchange",
    "exchange_tags": ["nlp", "public"],
    "exchange_metadata": {"owner": "team-nlp", "region": "us-east"}
  }'
```

→ `201 { "ok": true, "data": <ExchangeEntry> }`, with
`exchange_status: "healthy"` and `last_health_check_time` set.

**Failure modes:**

| Status | When |
|---|---|
| `400` | `exchange_id` or `exchange_api_url` missing |
| `400` | Health probe failed. The error reads `exchange not reachable at <url>: <reason>`. Nothing is persisted. |
| `409` | An entry with this `exchange_id` already exists. Use `PATCH` to change it, or `DELETE` first. |
| `500` | The DB insert itself failed |

### Read

```bash
curl http://localhost:5000/exchanges/demo-exchange
```
→ `200 { "ok": true, "data": <ExchangeEntry> }`, or `404` if not registered.

### Update

`PUT` and `PATCH` behave identically: the body is applied as a raw Mongo
`$set`, so dotted paths like `"exchange_metadata.region"` work.

```bash
curl -X PATCH http://localhost:5000/exchanges/demo-exchange \
  -H "Content-Type: application/json" \
  -d '{"exchange_tags": ["nlp", "public", "fr"], "exchange_metadata.region": "eu-west"}'
```
→ `200 { "ok": true, "data": <updated ExchangeEntry> }`.

Rules:

- Server-managed fields ([§2.1](02-schema.md#21-exchangeentry)) in the body
  are dropped.
- `exchange_id` can't be changed. A body with a *different* `exchange_id`
  gets `400`; repeating the same value is harmless.
- Changing `exchange_api_url` to a different URL resets `exchange_status` to
  `unknown`, since the old health result says nothing about the new URL. The
  next background check, or a manual
  `POST /exchanges/{id}/health-check`, fills it in. The update itself does
  **not** probe the new URL.
- `404` if the exchange isn't registered.

### Delete

```bash
curl -X DELETE http://localhost:5000/exchanges/demo-exchange
```
→ `200 { "ok": true, "data": {"deleted": true} }`, or `404` if not
registered. This only removes the registry entry. The exchange-db
deployment and its data are untouched.

### Query

`POST /exchanges/query` takes a raw Mongo filter, the same convention as
exchange-db's `/tasks/query` and `/subjects/query`. Because the filter is
passed straight to `collection.find()`, any valid Mongo query operator works.

```bash
# every exchange tagged "nlp"
curl -X POST http://localhost:5000/exchanges/query \
  -H "Content-Type: application/json" \
  -d '{"exchange_tags": {"$in": ["nlp"]}}'

# every exchange that failed its last health check
curl -X POST http://localhost:5000/exchanges/query \
  -H "Content-Type: application/json" \
  -d '{"exchange_status": "unreachable"}'
```
→ `200 { "ok": true, "data": [<ExchangeEntry>, ...] }`, or `400` for an
invalid filter. For combined registry + subject searches, use
[`/discover`](04-discovery.md) instead.

### Manual health check

```bash
curl -X POST http://localhost:5000/exchanges/demo-exchange/health-check
```
→ `200 { "ok": true, "data": <ExchangeEntry> }` with fresh
`exchange_status` / `last_health_check_time` / `last_health_check_error`.
The response is `200` even when the exchange is down; check
`data.exchange_status`. `404` if not registered.

## 3.3 Gateway forwarding

`GET | POST | PUT | PATCH | DELETE /exchanges/{exchange_id}/api/<path>`

The gateway looks up `exchange_id` in the registry and sends the request on
to `{exchange_api_url}/<path>`, preserving the method, the query string, the
raw request body and its `Content-Type`. The response is returned exactly as
the exchange produced it, with the same status code, body and `Content-Type`.

Every exchange-db endpoint ([Exchange System §3](../exchange-system/03-apis.md))
is reachable this way:

| Through the gateway | Forwarded to exchange-db |
|---|---|
| `POST /exchanges/{id}/api/tasks` | `POST /tasks` |
| `GET /exchanges/{id}/api/tasks/{task_id}` | `GET /tasks/{task_id}` |
| `GET /exchanges/{id}/api/tasks/{task_id}/output` | `GET /tasks/{task_id}/output` |
| `POST /exchanges/{id}/api/tasks/query` | `POST /tasks/query` |
| `POST /exchanges/{id}/api/subjects` | `POST /subjects` |
| `GET` / `PUT` / `PATCH` / `DELETE /exchanges/{id}/api/subjects/{subject_id}` | same method on `/subjects/{subject_id}` |
| `POST /exchanges/{id}/api/subjects/query` | `POST /subjects/query` |

```bash
# submit a direct-mode task to demo-exchange, without knowing where it runs
curl -X POST http://localhost:5000/exchanges/demo-exchange/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_assignment_type": "direct",
    "task_data": {"instruction": "summarize this document", "doc_url": "https://storage.example.com/report.pdf"},
    "task_metadata": {"task_assignment": {"subject_id": "agent-summarizer-01"}}
  }'

# poll its output
curl http://localhost:5000/exchanges/demo-exchange/api/tasks/<task_id>/output
```

**Gateway-originated errors** (everything else comes from the exchange):

| Status | Body | When |
|---|---|---|
| `404` | `{"ok": false, "error": "exchange not found"}` | `exchange_id` isn't registered |
| `502` | `{"ok": false, "error": "exchange '<id>' unreachable: <reason>"}` | Connection refused, DNS failure, or no response within the read timeout |

Notes:

- **The gateway never checks `exchange_status` before forwarding.** An
  `unreachable` exchange still gets the request. If it has recovered, the
  call succeeds; if not, you get a `502`.
- **Timeouts:** `(10, PROXY_READ_TIMEOUT)` seconds `(connect, read)`, default
  read timeout `300`. That's long enough for `function`-mode `POST /tasks`,
  which blocks on a selector-function call
  ([Exchange System §4.2](../exchange-system/04-assignment-modes.md#42-function-mode)).
- **One exchange per call.** Forwarding never fans out. Cross-exchange
  queries are discovery's job ([§4](04-discovery.md)).

## 3.4 Gateway health

```bash
curl http://localhost:5000/health
```
→ `200 { "ok": true, "data": {"status": "ok"} }`. This is a liveness check
for the gateway process only. It doesn't touch MongoDB or any exchange.

## 3.5 Full reference

| Method | Path | Section |
|---|---|---|
| `POST` | `/exchanges` | [§3.2 Register](#register) |
| `GET` | `/exchanges/{exchange_id}` | [§3.2 Read](#read) |
| `PUT` / `PATCH` | `/exchanges/{exchange_id}` | [§3.2 Update](#update) |
| `DELETE` | `/exchanges/{exchange_id}` | [§3.2 Delete](#delete) |
| `POST` | `/exchanges/query` | [§3.2 Query](#query) |
| `POST` | `/exchanges/{exchange_id}/health-check` | [§3.2 Manual health check](#manual-health-check) |
| `POST` | `/discover` | [§4](04-discovery.md) |
| any | `/exchanges/{exchange_id}/api/<path>` | [§3.3](#33-gateway-forwarding) |
| `GET` | `/health` | [§3.4](#34-gateway-health) |

---
[← Previous: Schema](02-schema.md) · [Back to index](README.md) · [Next: Discovery →](04-discovery.md)
