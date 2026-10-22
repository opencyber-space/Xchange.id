[← Back to index](README.md)

# 2. Schema

Both entities are plain dataclasses (`exchange-db/core/schema.py`) that
round-trip through `to_dict()` / `from_dict()` and are stored as-is (no
ORM/mapping layer) as MongoDB documents.

## 2.1 `ExchangeTasks`

Represents one unit of work submitted to the exchange.

| Field | Type | Required | Description |
|---|---|---|---|
| `task_id` | `string` | auto | Primary key. Generated server-side (`uuid4()`) by the API if omitted from the request; the dataclass itself has no default. |
| `task_assignment_type` | `string` | **yes** | One of `"direct"`, `"function"`, `"open"`, `"bidding"` — see [§1.2](01-concepts.md#12-the-four-assignment-modes) and [§4](04-assignment-modes.md). |
| `task_data` | any | **yes** | The actual work payload. Free-form — sent verbatim to whichever subject ends up handling the task, and to selector/evaluation functions. Not interpreted by Xchange. |
| `task_assignment_status` | `string` | **yes** | Lifecycle state. API default `"pending"` on submission; then mutated by `TaskAssignmentService` — see the status table in [§1.2](01-concepts.md#12-the-four-assignment-modes). |
| `task_metadata` | `object` | no (`{}`) | Free-form metadata. Its `task_assignment` sub-key carries mode-specific parameters (`subject_id` for `direct`, `function_id`/`parameters` for `function`, `bid_job_*` fields for `bidding`; unused for `open`). `bidding` mode also writes `task_metadata.bid_job_id` back onto this object once the bid job is created. |
| `taski_creation_time` | `datetime` (ISO-8601 string over the wire) | auto | Set by the API to the submission time. **Note the field name has a typo (`taski_` not `task_`) — this is intentional/as-specified, not a bug to silently rename.** |
| `task_output` | `object` | no (`{}`) | Populated once the task resolves: either the delegate system's response (`direct`/`function`/`open`) or Orcade's `bid_winner` task-result (`bidding`), or `{"error": "..."}` on failure/rejection. |

**Example — full `ExchangeTasks` document (`direct` mode, completed):**

```json
{
  "task_id": "3f9c6d2e-1a2b-4c3d-9e8f-7a6b5c4d3e2f",
  "task_assignment_type": "direct",
  "task_data": {"instruction": "summarize this document", "doc_url": "https://..."},
  "task_assignment_status": "completed",
  "task_metadata": {
    "task_assignment": {"subject_id": "agent-summarizer-01"}
  },
  "taski_creation_time": "2026-09-17T10:15:32.481203",
  "task_output": {"summary": "...", "acknowledged": true}
}
```

**Example — `bidding` mode, in flight:**

```json
{
  "task_id": "6b1a2c3d-4e5f-6789-0abc-def012345678",
  "task_assignment_type": "bidding",
  "task_data": {"task_type": "translate_document", "word_count": 4200},
  "task_assignment_status": "bidding",
  "task_metadata": {
    "task_assignment": {
      "bid_job_evaluator_id": "lowest-cost-evaluator:1.0-stable",
      "bid_job_pqt_id": "min-confidence-pqt:1.0-stable",
      "bid_job_subject_ids": ["agent-translator-01", "agent-translator-02"]
    },
    "bid_job_id": "8f14e45f-ceea-4a19-8f6e-8b5a9c1a9f10"
  },
  "taski_creation_time": "2026-09-17T10:20:00.000000",
  "task_output": {}
}
```

## 2.2 `ExchangeSubjects`

Represents one agent registered with this exchange.

| Field | Type | Required | Description |
|---|---|---|---|
| `subject_id` | `string` | auto | Primary key. Generated server-side (`uuid4()`) by the API if omitted. |
| `subject_metadata` | `object` | no (`{}`) | Free-form metadata about the subject (capabilities summary, owner, tags, ...). Not interpreted by Xchange itself. |
| `task_evaluation_function` | `string` | no (`""`) | `function_id` in the function registry, invoked by `open`-mode assignment to ask this subject whether it accepts a given task. Empty string means this subject is skipped entirely during `open` evaluation (see [§4.3](04-assignment-modes.md#43-open-mode)). |
| `subject_capabilities` | `object` | no (`{}`) | Free-form description of what the subject can do. Passed through to selector/evaluation functions as part of the subject's `to_dict()`; not filtered or matched against task requirements by Xchange itself. |
| `topics` | `array<string>` | no (`[]`) | Tags used only by `bidding`-mode assignment to narrow the default subject pool for a bid job — see [§4.4](04-assignment-modes.md#44-bidding-mode) and [§7.2](07-bidding-mode.md#72-creating-the-bid-job). Not consulted by any other assignment mode. |

**Example — full `ExchangeSubjects` document:**

```json
{
  "subject_id": "agent-summarizer-01",
  "subject_metadata": {"owner": "team-nlp", "region": "us-east"},
  "task_evaluation_function": "accepts-if-capacity:1.0-stable",
  "subject_capabilities": {"max_doc_tokens": 50000, "languages": ["en", "fr"]},
  "topics": ["summarization", "nlp"]
}
```

## 2.3 `to_dict()` / `from_dict()` notes

- `taski_creation_time` round-trips as an ISO-8601 string via `to_dict()`
  (`datetime.isoformat()`) and is parsed back with `datetime.fromisoformat()`
  in `from_dict()`; a `None` value passes through unchanged in both
  directions.
- All `dict`-typed fields default to a fresh `{}` (via `field(default_factory=dict)`)
  when omitted from `from_dict()`'s input — there is no `None` vs `{}`
  ambiguity to handle downstream.

## 2.4 Storage

Both entities live in MongoDB (`MONGO_URL`), in a database named
`exchange_{EXCHANGE_ID}` — i.e. **each exchange deployment gets its own
database**, computed at runtime by `crud.get_db_name()`. This is also why
"list every subject associated with the exchange" ([§1.1](01-concepts.md#11-actors))
needs no filter anywhere in the code — every document in that database
belongs to this exchange by construction.

| Collection | Document key used as Mongo `_id` |
|---|---|
| `tasks` | `task_id` |
| `subjects` | `subject_id` |

`ExchangeTasksCRUD` / `ExchangeSubjectsCRUD` (`exchange-db/core/crud.py`)
expose `create` / `get` / `list(query={})` / `update(id, {field: value})` /
`delete`. `update()` applies its `updates` dict as a raw MongoDB `$set` —
including dotted paths like `"task_metadata.bid_job_id"` — with no schema
validation. `list()` accepts a **raw MongoDB filter document**, same
convention as Orcade's `*_db.query()`.

---
[← Previous: Concepts](01-concepts.md) · [Back to index](README.md) · [Next: APIs →](03-apis.md)
