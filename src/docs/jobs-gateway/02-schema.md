[← Back to index](README.md)

# 2. Schema

The registry has a single entity, a plain dataclass
(`jobs-gateway/core/schema.py`) that round-trips through `to_dict()` /
`from_dict()` and is stored as-is as a MongoDB document. It follows the same
conventions as exchange-db's `ExchangeTasks` / `ExchangeSubjects`.

## 2.1 `ExchangeEntry`

Represents one registered exchange-db instance.

| Field | Type | Required | Description |
|---|---|---|---|
| `exchange_id` | `string` | **yes** | Primary key. It should equal the exchange's own `EXCHANGE_ID` env var, though the gateway doesn't verify that. It cannot be changed after registration. |
| `exchange_api_url` | `string` | **yes** | Base URL of the exchange's REST API, e.g. `http://demo-exchange-svc.exchanges.svc.cluster.local:5000`. A trailing `/` is stripped on write. Every gateway → exchange call is built from this. |
| `exchange_name` | `string` | no (`""`) | Human-readable name. Not interpreted. |
| `exchange_description` | `string` | no (`""`) | Free-text description. Not interpreted. |
| `exchange_tags` | `array<string>` | no (`[]`) | Tags used by discovery's `tags` filter (`{"exchange_tags": {"$in": tags}}`), see [§4.2](04-discovery.md#42-stage-1-registry-filter). |
| `exchange_metadata` | `object` | no (`{}`) | Free-form metadata (owner, region, cost tier, ...). Queryable with dotted paths through `/exchanges/query` or discovery's `query`. Not interpreted by the gateway. |
| `exchange_status` | `string` | server-managed | `"unknown"`, `"healthy"` or `"unreachable"`, see [§1.3](01-concepts.md#13-exchange-status). |
| `registration_time` | `datetime` (ISO-8601 string over the wire) | server-managed | Set once, when the entry is created. |
| `last_health_check_time` | `datetime` (ISO-8601) or `null` | server-managed | Time of the most recent probe, or `null` if none has run. |
| `last_health_check_error` | `string` | server-managed | Error from the most recent failed probe, or `""` after a successful one. |

**Server-managed fields** (`exchange_status`, `registration_time`,
`last_health_check_time`, `last_health_check_error`) are silently dropped
if a caller sends them in `POST /exchanges` or `PUT`/`PATCH /exchanges/{id}`.
Only the gateway's own health checks write them.

**Example: full `ExchangeEntry` document:**

```json
{
  "exchange_id": "demo-exchange",
  "exchange_api_url": "http://demo-exchange-svc.exchanges.svc.cluster.local:5000",
  "exchange_name": "Demo exchange",
  "exchange_description": "NLP tasks for the demo org",
  "exchange_tags": ["nlp", "public"],
  "exchange_metadata": {"owner": "team-nlp", "region": "us-east"},
  "exchange_status": "healthy",
  "registration_time": "2026-10-22T09:00:00.000000",
  "last_health_check_time": "2026-10-22T09:41:30.512044",
  "last_health_check_error": ""
}
```

## 2.2 `to_dict()` / `from_dict()` notes

- `registration_time` and `last_health_check_time` are serialized with
  `datetime.isoformat()` and parsed back with `datetime.fromisoformat()`. A
  `None` passes through unchanged in both directions.
- `exchange_tags` defaults to `[]` and `exchange_metadata` to `{}` when
  missing, so downstream code never has to deal with `None`.

## 2.3 Storage

Entries live in MongoDB (`MONGO_URL`), database `GATEWAY_DB_NAME` (default
`xchange_gateway`), collection `exchanges`, with `exchange_id` used as the
Mongo `_id`. Because the database name is configurable, the gateway can share
a MongoDB server with the exchanges themselves (which use
`exchange_{EXCHANGE_ID}`) without colliding.

`ExchangeRegistryCRUD` (`jobs-gateway/core/crud.py`) exposes `create` /
`get` / `list(query={})` / `update(id, {field: value})` / `delete`, with the
same semantics as exchange-db's CRUD classes: `update()` is a raw `$set`
(dotted paths allowed, no schema validation) and `list()` takes a raw Mongo
filter.

---
[← Previous: Concepts](01-concepts.md) · [Back to index](README.md) · [Next: APIs →](03-apis.md)
