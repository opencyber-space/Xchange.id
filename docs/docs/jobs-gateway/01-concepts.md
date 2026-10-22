[← Back to index](README.md)

# 1. Concepts

## 1.1 Actors

- **Exchange** (`exchange-db` instance): one deployment of the exchange
  service, identified by its `EXCHANGE_ID` env var. It owns its tasks and
  subjects and serves the REST API documented in
  [Exchange System §3](../exchange-system/03-apis.md). Exchanges don't know
  the gateway exists. Nothing in exchange-db calls the gateway.
- **Registry entry** (`ExchangeEntry`): the gateway's record of one
  exchange: its `exchange_id`, the base URL it's reachable at
  (`exchange_api_url`), tags, free-form metadata and the latest health-check
  result. See [§2](02-schema.md).
- **Jobs gateway**: a single stateless Flask service plus its own MongoDB
  database (`GATEWAY_DB_NAME`, default `xchange_gateway`) holding the
  registry. It plays three roles, described below.
- **Caller**: anything that wants to work with exchanges without knowing
  where they run: an agent, an orchestrator, a UI, another service.

## 1.2 The three roles

```
                          ┌───────────────────────── jobs-gateway ─────────────────────────┐
                          │                                                                │
 caller ── /exchanges ───►│  Registry   ── CRUD ──► Mongo: xchange_gateway.exchanges       │
                          │                                                                │
 caller ── /discover ────►│  Discovery  ── filter registry ──► candidates                  │
                          │               └─ (optional) POST /subjects/query ──────────────┼──► exchange-db A
                          │                  to every candidate, in parallel ──────────────┼──► exchange-db B
                          │                                                                │
 caller ── /exchanges/{id}/api/<path> ──► Gateway ── look up URL ── forward as-is ─────────┼──► exchange-db {id}
                          │                                                                │
                          │  HealthChecker (background, every HEALTH_CHECK_INTERVAL s) ────┼──► every exchange-db
                          └────────────────────────────────────────────────────────────────┘
```

**Registry.** Plain CRUD over `ExchangeEntry` records, plus a raw-Mongo-filter
query endpoint, following the same conventions as exchange-db's own subject
CRUD. Registration probes the exchange first and refuses to register one it
can't reach, unless the caller passes `skip_health_check: true`. See
[§3.2](03-apis.md#32-registry).

**Discovery.** Answers *"which exchanges should I send this work to?"*. It
works in two stages:

1. Filter the registry by tags, status and/or any raw Mongo filter. This
   step is local and costs nothing.
2. Optionally, ask each remaining exchange which of **its** subjects match a
   subject filter (for example `topics` containing `"summarization"`). Only
   exchanges with at least one match are returned, each listing the IDs of
   its matching subjects.

Stage 2 is the only place the gateway joins data across exchanges. See
[§4](04-discovery.md).

**Gateway.** `/exchanges/{exchange_id}/api/<path>` forwards any method, query
string and body to `{exchange_api_url}/<path>` and returns the exchange's
response untouched: same status code, same `{"ok": ..., "data"/"error": ...}`
envelope. Anything you can do against an exchange-db directly you can do
through the gateway by `exchange_id`. See [§3.3](03-apis.md#33-gateway-forwarding).

## 1.3 Exchange status

Every registry entry carries an `exchange_status`:

| Value | Meaning |
|---|---|
| `unknown` | Never checked. This happens when the entry was registered with `skip_health_check: true`, or its `exchange_api_url` was just changed and the background checker hasn't run yet. |
| `healthy` | The most recent health probe got a valid exchange-db response. |
| `unreachable` | The most recent probe failed. The reason is in `last_health_check_error`. |

Status is **informational**. It never blocks anything on its own: the
gateway still forwards requests to an `unreachable` exchange, and discovery
still returns it unless you filter with `"status": "healthy"`. See
[§5](05-health-checks.md).

## 1.4 What the gateway does not do

- **No provisioning.** It doesn't deploy exchange-db instances. Deploy one
  (e.g. `k8s/deploy.yaml`) and then register it.
- **No self-registration.** exchange-db doesn't register itself on startup.
  Registration is an explicit `POST /exchanges` call, made by whoever
  deployed the exchange.
- **No routing decisions on task submission.** The gateway never picks an
  exchange for you when you submit a task. Use `/discover` to choose, then
  submit through `/exchanges/{id}/api/tasks`.
- **No caching or aggregation of tasks.** Task state lives only in each
  exchange. To find a task, you need to know which exchange it was submitted
  to.
- **No auth/ACL layer.** It is meant for trusted networks only, like
  exchange-db and Orcade.

---
[← Back to index](README.md) · [Next: Schema →](02-schema.md)
