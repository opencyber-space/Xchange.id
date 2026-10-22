[← Back to index](README.md)

# 6. How a task reaches a subject via the delegate system

Applies to `direct`, `function`, and `open` mode. **`bidding` mode does not
use this path at all** — Orcade talks to subjects on Xchange's behalf; see
[§7](07-bidding-mode.md).

Like Orcade, Xchange never talks to a subject/agent directly. Every
submission goes through `SubjectTask` (`exchange-db/core/subject_task.py`)
— **the exact same class, copied verbatim from Orcade** — against the same
kind of external **delegate service** at `SUBJECT_DELEGATE_URL`.

## 6.1 Transport

```
POST {SUBJECT_DELEGATE_URL}/api/submit-and-wait
```

```json
{
  "subject_id": "agent-summarizer-01",
  "session_id": "3f9c6d2e-1a2b-4c3d-9e8f-7a6b5c4d3e2f",
  "task_id": "3f9c6d2e-1a2b-4c3d-9e8f-7a6b5c4d3e2f",
  "task_data": { "...": "the task's task_data field, verbatim" }
}
```

| Field | Value in Xchange's usage |
|---|---|
| `subject_id` | the resolved target subject (fixed for `direct`, picked by the selector function for `function`, the first accepter for `open`) |
| `session_id` | **the `task_id`** — note this differs from Orcade, where `session_id` is the `bid_job_id` and `task_id` is a fresh UUID generated per call. In Xchange, both fields are always the same value: the exchange task's own `task_id`. |
| `task_id` | same as `session_id` — see above |
| `task_data` | **the exchange task's `task_data`, sent as-is** — unlike Orcade, Xchange does not wrap it in an envelope object with a `"type"` discriminator (Orcade's `bid_request`/`bid_winner` shape). The subject receives exactly what was submitted in `POST /tasks`, nothing more. |

The call is a **blocking** `requests.post(...)` with a `(10, 300)` second
`(connect, read)` timeout, identical to Orcade — Xchange waits up to 5
minutes for the delegate/subject to respond before the call fails.

## 6.2 What Xchange does with the subject's response

Whatever JSON the delegate returns becomes `task_output` verbatim, and
`task_assignment_status` is set to `"completed"`:

```python
result = self._subject_task.submit_and_wait(subject_id=subject_id, session_id=task.task_id, task_id=task.task_id, task_data=task.task_data)
self._tasks_crud.update(task.task_id, {"task_output": result, "task_assignment_status": "completed"})
```

Nothing in `TaskAssignmentService` reads specific fields back out of this
response — there's no "subject declined" branch once submission has
started (declining only happens *before* submission, in `open` mode's
evaluation step, via the separate task-evaluation function call, see
[§5.2](05-functions.md#52-task-evaluation-function-open-mode)).

If the delegate call raises (timeout, non-2xx, connection error), the error
is logged, `task_assignment_status` is set to `"failed"`, and `task_output`
becomes `{"error": "<exception message>"}`. There is no retry mechanism —
same as Orcade.

---
[← Previous: Functions to write](05-functions.md) · [Back to index](README.md) · [Next: Bidding mode integration →](07-bidding-mode.md)
