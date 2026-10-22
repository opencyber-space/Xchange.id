[← Back to index](README.md)

# 4. Discovery

`POST /discover` answers *"which exchanges should I send this work to?"* It
is implemented by `DiscoveryService` (`jobs-gateway/core/discovery.py`) and
runs in two stages:

```
POST /discover
   │
   ├─► stage 1: filter the registry (local Mongo query)            → candidate exchanges
   │
   └─► stage 2 (only if a subject filter was given):
         for every candidate, in parallel:
             POST {exchange_api_url}/subjects/query  <subject filter>
         keep exchanges with ≥ 1 matching subject, sorted by match count (desc)
```

## 4.1 Request body

Every field is optional. An empty body `{}` returns every registered
exchange.

| Field | Type | Stage | Meaning |
|---|---|---|---|
| `tags` | array&lt;string&gt; | 1 | Keep exchanges whose `exchange_tags` contain **any** of these (`$in`). |
| `status` | string | 1 | Keep exchanges whose `exchange_status` equals this, typically `"healthy"`. |
| `query` | object | 1 | Raw Mongo filter over registry entries, e.g. `{"exchange_metadata.region": "us-east"}`. |
| `subject_topics` | array&lt;string&gt; | 2 | Match subjects whose `topics` contain **any** of these (`{"topics": {"$in": ...}}`), the same filter exchange-db's `bidding` mode uses ([Exchange System §7.2](../exchange-system/07-bidding-mode.md#72-creating-the-bid-job)). |
| `subject_query` | object | 2 | Raw Mongo filter over `ExchangeSubjects` documents, e.g. `{"subject_capabilities.max_doc_tokens": {"$gte": 100000}}`. |

## 4.2 Stage 1: registry filter

`tags`, `status` and `query` are each turned into one filter and combined
with `$and`:

```python
filters = []
if query:  filters.append(query)
if tags:   filters.append({"exchange_tags": {"$in": tags}})
if status: filters.append({"exchange_status": status})
registry_query = {"$and": filters} if len(filters) > 1 else (filters[0] if filters else {})
```

This stage only reads the gateway's own registry. It never contacts an
exchange, so it's cheap and always available. With no subject filter, the
result is simply the matching registry entries, in Mongo's natural order.

## 4.3 Stage 2: subject fan-out

If `subject_topics` and/or `subject_query` is given, they're combined the
same way (`$and` when both are present) into one subject filter. Then, for
**every** stage-1 candidate:

```
POST {exchange_api_url}/subjects/query    body: <subject filter>
```

- Calls run **in parallel** on a thread pool of `DISCOVERY_WORKERS` threads
  (default 8), each with a `(5, 30)` second `(connect, read)` timeout. One
  hung exchange costs at most about 35 seconds on its own thread and never
  fails the whole request.
- An exchange with **zero** matching subjects is dropped from the result.
- An exchange whose call fails (transport error, non-2xx, or `"ok": false`)
  is **not** dropped silently. It goes into the `unreachable` list with the
  error, so callers can tell *"has no matching subjects"* apart from
  *"couldn't ask"*.
- Results are sorted by number of matching subjects, highest first.

Stage 2 doesn't consult `exchange_status`. A cheap way to skip known-down
exchanges is to add `"status": "healthy"` to stage 1.

## 4.4 Response

```json
{
  "ok": true,
  "data": {
    "exchanges": [ <ExchangeEntry>, ... ],
    "unreachable": [ {"exchange_id": "...", "error": "..."}, ... ]
  }
}
```

- **Without a subject filter:** `exchanges` holds the stage-1 entries as-is,
  and `unreachable` is always `[]`.
- **With a subject filter:** each item in `exchanges` is a full
  `ExchangeEntry` plus a `matching_subject_ids` array.

`400` with `{"ok": false, "error": ...}` if a filter is invalid, e.g. a
malformed operator in `query`.

## 4.5 Examples

**All healthy exchanges tagged `nlp`:**

```bash
curl -X POST http://localhost:5000/discover \
  -H "Content-Type: application/json" \
  -d '{"tags": ["nlp"], "status": "healthy"}'
```

**Healthy exchanges that have at least one summarization subject:**

```bash
curl -X POST http://localhost:5000/discover \
  -H "Content-Type: application/json" \
  -d '{"status": "healthy", "subject_topics": ["summarization"]}'
```

```json
{
  "ok": true,
  "data": {
    "exchanges": [
      {
        "exchange_id": "demo-exchange",
        "exchange_api_url": "http://demo-exchange-svc.exchanges.svc.cluster.local:5000",
        "exchange_name": "Demo exchange",
        "exchange_description": "",
        "exchange_tags": ["nlp", "public"],
        "exchange_metadata": {"owner": "team-nlp"},
        "exchange_status": "healthy",
        "registration_time": "2026-10-22T09:00:00.000000",
        "last_health_check_time": "2026-10-22T09:41:30.512044",
        "last_health_check_error": "",
        "matching_subject_ids": ["agent-summarizer-01", "agent-summarizer-02"]
      },
      {
        "exchange_id": "eu-exchange",
        "...": "...",
        "matching_subject_ids": ["agent-summarizer-eu"]
      }
    ],
    "unreachable": []
  }
}
```

**US exchanges with a subject that can handle long documents, combining a
registry filter with a capability filter:**

```bash
curl -X POST http://localhost:5000/discover \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"exchange_metadata.region": "us-east"},
    "subject_topics": ["summarization"],
    "subject_query": {"subject_capabilities.max_doc_tokens": {"$gte": 100000}}
  }'
```

## 4.6 Using the result

Discovery only *finds* exchanges. It doesn't submit anything. A typical
caller picks one entry (the first, i.e. the most matching subjects, or by
its own criteria) and then submits through the gateway:

- `direct` mode, using one of `matching_subject_ids` as `subject_id`;
- `bidding` mode, passing `matching_subject_ids` as `bid_job_subject_ids`,
  or the same `topics` you discovered with;
- `function` / `open` mode, letting the exchange choose among its own
  subjects.

See [§6.3](06-deployment.md#63-end-to-end-walkthrough) for a full example.

Matches reflect the exchanges' subjects **at discovery time**. A subject can
be deleted or re-tagged between `/discover` and submission. exchange-db
handles that the same way it would without the gateway (e.g. a `direct`-mode
task to a missing subject ends in `failed`).

---
[← Previous: APIs](03-apis.md) · [Back to index](README.md) · [Next: Health checks →](05-health-checks.md)
