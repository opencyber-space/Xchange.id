[← Back to index](README.md)

# 3. APIs

Base path: none (routes are mounted at root). Default port `5000`
(`run_server()` in `exchange-db/core/apis.py`; the `PORT` env var set in the
k8s manifest is informational only — like Orcade, Flask's dev server itself
is hardcoded to `0.0.0.0:5000` in `run_server()`).

## 3.1 Response envelope

Every endpoint replies with the same envelope, identical to Orcade's:

```json
// success
{ "ok": true, "data": { ... } }

// failure
{ "ok": false, "error": "human readable message" }
```

## 3.2 How to submit a task

`POST /tasks`

Persists the task, then synchronously calls
`TaskAssignmentService.assign()` — for `function` mode this includes the
(blocking) selector-function call; for every mode, the actual delegate
submission always happens on a background thread (see
[§1.2](01-concepts.md#12-the-four-assignment-modes)).

**Request body:**

| Field | Type | Default if omitted |
|---|---|---|
| `task_id` | string | server-generated `uuid4()` |
| `task_assignment_type` | string | **required** — `400` if missing |
| `task_data` | any | **required** — `400` if missing |
| `task_assignment_status` | string | `"pending"` |
| `task_metadata` | object | `{}` |

```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_assignment_type": "direct",
    "task_data": {"instruction": "summarize this document", "doc_url": "https://storage.example.com/report.pdf"},
    "task_metadata": {
      "task_assignment": {"subject_id": "agent-summarizer-01"}
    }
  }'
```

**Response `201 Created`:**

```json
{
  "ok": true,
  "data": {
    "task_id": "3f9c6d2e-1a2b-4c3d-9e8f-7a6b5c4d3e2f",
    "task_assignment_type": "direct",
    "task_data": {"instruction": "summarize this document", "doc_url": "https://storage.example.com/report.pdf"},
    "task_assignment_status": "pending",
    "task_metadata": {"task_assignment": {"subject_id": "agent-summarizer-01"}},
    "taski_creation_time": "2026-09-17T10:15:32.481203",
    "task_output": {}
  }
}
```

The response is a snapshot from the moment of submission — for `function`
mode `task_assignment_status` will already read `"assigned"` in the
*persisted* record (fetch it again via [§3.3](#33-how-to-read-a-task) to see
that), but the object returned inline by this call always reflects the
in-memory `task` object as it was right after `assign()` returned, so check
back with a `GET` rather than trusting this response for anything beyond
`task_id`.

**Failure modes:**

| Status | When |
|---|---|
| `400` | `task_assignment_type` or `task_data` missing from the body |
| `400` | `assign()` raised synchronously — unsupported `task_assignment_type`, missing `subject_id`/`function_id` in `task_metadata.task_assignment`, or the selector function (in `function` mode) raised / didn't return `selected_subject_id`. The task is still persisted, marked `task_assignment_status="failed"` with the error in `task_output`. |
| `500` | The initial DB insert itself failed |

## 3.3 How to read a task

`GET /tasks/{task_id}` — full record.

```bash
curl http://localhost:5000/tasks/3f9c6d2e-1a2b-4c3d-9e8f-7a6b5c4d3e2f
```
→ `200 { "ok": true, "data": <ExchangeTasks> }`, or `404` if not found.

## 3.4 How to read task output

`GET /tasks/{task_id}/output` — just the two fields callers usually poll for.

```bash
curl http://localhost:5000/tasks/3f9c6d2e-1a2b-4c3d-9e8f-7a6b5c4d3e2f/output
```
```json
{
  "ok": true,
  "data": {
    "task_assignment_status": "completed",
    "task_output": {"summary": "...", "acknowledged": true}
  }
}
```
→ `404` if the task doesn't exist. There is no long-poll / websocket
mode — callers are expected to poll this endpoint themselves.

## 3.5 Task endpoints — full reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/tasks` | Submit a task (§3.2) |
| `GET` | `/tasks/{task_id}` | Fetch one task by ID (§3.3) |
| `GET` | `/tasks/{task_id}/output` | Fetch just status + output (§3.4) |
| `POST` | `/tasks/query` | Query tasks with a raw Mongo filter |

There is intentionally **no `PUT`/`PATCH`/`DELETE` for tasks** in this API —
unlike Orcade's bid jobs, task state is only ever mutated internally by
`TaskAssignmentService`, not by API callers.

```bash
# every task currently sitting in "bidding"
curl -X POST http://localhost:5000/tasks/query \
  -H "Content-Type: application/json" \
  -d '{"task_assignment_status": "bidding"}'

# every open-mode task that got rejected by all subjects
curl -X POST http://localhost:5000/tasks/query \
  -H "Content-Type: application/json" \
  -d '{"task_assignment_type": "open", "task_assignment_status": "rejected"}'
```

Because the filter is passed straight to `collection.find()`, any valid
Mongo query operator works (`$gt`, `$in`, `$exists`, ...). No projection
support, no auth/ACL layer — trusted-network only, same as Orcade.

## 3.6 Subjects — full reference {#subjects}

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/subjects` | Create a subject |
| `GET` | `/subjects/{subject_id}` | Fetch one subject |
| `PUT` / `PATCH` | `/subjects/{subject_id}` | Raw `$set` update; `404` if the subject doesn't exist |
| `DELETE` | `/subjects/{subject_id}` | Delete a subject; `404` if it didn't exist |
| `POST` | `/subjects/query` | Query subjects with a raw Mongo filter |

**Create:**

```bash
curl -X POST http://localhost:5000/subjects \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "agent-summarizer-01",
    "subject_metadata": {"owner": "team-nlp"},
    "task_evaluation_function": "accepts-if-capacity:1.0-stable",
    "subject_capabilities": {"max_doc_tokens": 50000},
    "topics": ["summarization", "nlp"]
  }'
```
→ `201 { "ok": true, "data": <ExchangeSubjects> }`. `subject_id` is
server-generated if omitted.

**Update** (unlike Orcade's bid-job update, this one checks existence first
and returns the *fresh* document, not just a modified count):

```bash
curl -X PATCH http://localhost:5000/subjects/agent-summarizer-01 \
  -H "Content-Type: application/json" \
  -d '{"subject_capabilities": {"max_doc_tokens": 80000}}'
```
→ `200 { "ok": true, "data": <updated ExchangeSubjects> }`, or `404` if the
subject doesn't exist.

**Delete:**

```bash
curl -X DELETE http://localhost:5000/subjects/agent-summarizer-01
```
→ `200 { "ok": true, "data": {"deleted": true} }`, or `404` if not found.

**Query** — same raw-Mongo-filter convention as `/tasks/query`:

```bash
# every subject that participates in open-mode evaluation
curl -X POST http://localhost:5000/subjects/query \
  -H "Content-Type: application/json" \
  -d '{"task_evaluation_function": {"$ne": ""}}'

# every subject tagged with the "nlp" topic — the same filter
# bidding mode itself uses when a task specifies "topics" (§4.4, §7.2)
curl -X POST http://localhost:5000/subjects/query \
  -H "Content-Type: application/json" \
  -d '{"topics": {"$in": ["nlp"]}}'
```

---
[← Previous: Schema](02-schema.md) · [Back to index](README.md) · [Next: Assignment modes →](04-assignment-modes.md)
