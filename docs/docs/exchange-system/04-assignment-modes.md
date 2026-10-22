[← Back to index](README.md)

# 4. Assignment modes

All four modes are implemented as branches of
`TaskAssignmentService.assign()` (`exchange-db/core/task_assignment.py`),
called once, synchronously, from inside the `POST /tasks` handler
(`exchange-db/core/apis.py`). Every mode ends the same way — a call to the
private `_submit_and_save()` helper, which does the actual delegate
round-trip and writes `task_output` / `task_assignment_status` back to
Mongo:

```python
def _submit_and_save(self, task, subject_id):
    try:
        result = self._subject_task.submit_and_wait(
            subject_id=subject_id,
            session_id=task.task_id,
            task_id=task.task_id,
            task_data=task.task_data,
        )
        self._tasks_crud.update(task.task_id, {"task_output": result, "task_assignment_status": "completed"})
    except Exception as e:
        self._tasks_crud.update(task.task_id, {"task_assignment_status": "failed", "task_output": {"error": str(e)}})
```

The four modes differ only in **how `subject_id` gets decided** and **which
parts of that decision happen synchronously vs. on a background thread**.
See [§6](06-delegate-system.md) for what `submit_and_wait` actually sends.

## 4.1 `direct` mode

**Config (`task_metadata.task_assignment`):**

| Field | Type | Required |
|---|---|---|
| `subject_id` | string | **yes** — `KeyError` (surfaces as the API's `400`) if missing |

**What happens:**

```python
def _handle_direct(self, task):
    subject_id = task.task_metadata["task_assignment"]["subject_id"]
    threading.Thread(target=self._submit_and_save, args=(task, subject_id), daemon=True).start()
```

No selection logic at all — the caller already knows who should do the work.
The only asynchronous part is the delegate round-trip itself; `POST /tasks`
returns immediately after the thread is started.

## 4.2 `function` mode

**Config (`task_metadata.task_assignment`):**

| Field | Type | Required |
|---|---|---|
| `function_id` | string | **yes** — `KeyError` if missing |
| `parameters` | object | no (`{}`) — forwarded as `FunctionCaller.call(..., parameters=...)` |

**What happens:**

```python
def _handle_function(self, task):
    assignment = task.task_metadata["task_assignment"]
    subjects = self._subjects_crud.list()                       # every subject in this exchange
    result = self._function_caller.call(
        function_id=assignment["function_id"],
        input_data={"task_data": task.task_data, "subjects": [s.to_dict() for s in subjects]},
        parameters=assignment.get("parameters", {}),
    )
    selected_subject_id = result["selected_subject_id"]          # raises if falsy/missing
    self._tasks_crud.update(task.task_id, {"task_assignment_status": "assigned"})
    threading.Thread(target=self._submit_and_save, args=(task, selected_subject_id), daemon=True).start()
```

This is the only mode with a **synchronous** step: the selector-function
call blocks the `POST /tasks` request. If it raises, or its response has no
truthy `selected_subject_id`, the exception propagates all the way up to the
API handler → `400`, and the task is marked `failed`. See
[§5.1](05-functions.md#51-selector-function-function-mode) for the function's
input/output contract.

Once a subject is selected, submission to that subject is still
backgrounded — same as `direct`.

## 4.3 `open` mode

**Config (`task_metadata.task_assignment`):** none — `open` mode ignores
this key entirely; every subject in the exchange is a candidate.

**What happens:**

```python
def _run_open_assignment(self, task):          # runs on a background thread from the start
    for subject in self._subjects_crud.list():
        if not subject.task_evaluation_function:
            continue                            # subjects with no evaluation function never participate
        try:
            result = self._function_caller.call(
                function_id=subject.task_evaluation_function,
                input_data={"task_data": task.task_data, "subject": subject.to_dict()},
            )
        except Exception:
            continue                            # a failing evaluator is treated as "did not accept"
        if result.get("status") == "accepted":
            self._tasks_crud.update(task.task_id, {"task_assignment_status": "assigned"})
            self._submit_and_save(task, subject.subject_id)     # inline — already on the background thread
            return
    self._tasks_crud.update(task.task_id, {"task_assignment_status": "rejected", "task_output": {"error": "no subject accepted the task"}})
```

Unlike `function` mode, **the entire flow — evaluating every subject and
submitting to the winner — runs on one background thread**, started
immediately when `POST /tasks` is handled. Nothing here is parallelized:
subjects are asked one at a time, in whatever order MongoDB returns them,
and the loop stops at the first `"status": "accepted"` response. If no
subject accepts (or the exchange has no subjects with a
`task_evaluation_function` set), the task ends in `task_assignment_status="rejected"`
with an explanatory `task_output.error` — this is a normal terminal state,
not a bug.

See [§5.2](05-functions.md#52-task-evaluation-function-open-mode) for the
per-subject evaluation function's input/output contract.

## 4.4 `bidding` mode

**Config (`task_metadata.task_assignment`):**

| Field | Type | Required | Notes |
|---|---|---|---|
| `bid_job_evaluator_id` | string | **yes** — `KeyError` if missing | Forwarded straight to Orcade |
| `bid_job_pqt_id` | string | no (`""`) | Forwarded straight to Orcade |
| `bid_job_tie_id` | string | no (`""`) | Forwarded straight to Orcade (inert on Orcade's side too) |
| `bid_job_metadata` | object | no (`{}`) | Forwarded straight to Orcade |
| `bid_job_description` | object | no (`{}`) | Forwarded straight to Orcade |
| `bid_job_name` | object | no (`{}`) | Forwarded straight to Orcade |
| `bid_job_creator_id` | string | no (`""`) | Forwarded straight to Orcade |
| `bid_job_subject_ids` | array&lt;string&gt; | no | Explicit subject list. |
| `topics` | array&lt;string&gt; | no | Resolved to every `ExchangeSubjects` whose own `topics` list intersects this one (`{"topics": {"$in": topics}}`). |
| `bid_job_mode` | string | no (`"closed"`) | `"closed"` (default), `"open"`, or `"mixed"`. Open and mixed modes are described below. |
| `bid_job_max_subjects` | integer | open mode | Forwarded to Orcade; job closes once this many subjects have applied. |
| `bid_job_max_time` | integer (seconds) | open mode | Forwarded to Orcade; job closes this many seconds after creation. |
| `bid_job_tags` | array&lt;string&gt; | no (`[]`) | Forwarded to Orcade. Subjects discover open jobs by these tags. |

**Open mode (`bid_job_mode: "open"`).** Subjects are not pre-selected: they
find the job on Orcade by `bid_job_tags` and apply themselves. Orcade closes
the job on `bid_job_max_subjects` or `bid_job_max_time` (or whichever comes
first) and evaluates the applicants. Consequently, open mode **rejects**
`bid_job_subject_ids` and `topics` synchronously (`400` from `POST /tasks`),
since neither has meaning there. Xchange's poller also stops early with
`task_assignment_status="rejected"` if the job closes with no applicants,
instead of waiting forever.

**Mixed mode (`bid_job_mode: "mixed"`).** A fixed, required roster like
`closed` mode — Orcade rejects a mixed-mode job with an empty
`bid_job_subject_ids` — but Orcade also auto-tags each named subject with
`subject::<subject_id>` on top of any `bid_job_tags` you supply, so a
subject can discover the job by tag (matching its own ID) as a fallback or
alternative to receiving the `bid_request` push notification. Both are still
sent in mixed mode — see Orcade's
[schema doc](https://openarcade-internal.pages.dev/bids-system/02-schema/) for the
tagging mechanics. From Xchange's side, mixed behaves identically to
`closed`: only `bid_job_mode == "open"` changes how the subject pool and the
polling loop are handled (see the code below), so `bid_job_subject_ids` /
`topics` resolution, `bid_job_max_subjects` / `bid_job_max_time` (which do
**not** apply here — Orcade rejects them for anything but `open`), and the
no-early-exit polling behavior are all exactly as described for `closed`
below.

For both `closed` and `mixed`: if **both** `bid_job_subject_ids` and
`topics` are given, the final subject pool is their **union**
(deduplicated, order-preserving) — not an intersection and not one taking
priority over the other. If only one is given, that one alone determines
the pool. If neither is given, the pool **defaults to every subject in this
exchange** (`ExchangeSubjectsCRUD.list()`) — for `mixed` mode this also
satisfies Orcade's "at least one subject" requirement as long as the
exchange isn't empty; if it is, job creation fails on Orcade's side and the
task is marked `failed`, the same way any other Orcade-side validation
failure is handled (e.g. a subject ID containing a comma).

**What happens:** the entire thing — job creation *and* polling for a
result — runs on one background thread, started immediately when
`POST /tasks` is handled:

```python
def _run_bidding(self, task):
    assignment = task.task_metadata["task_assignment"]
    explicit_subject_ids = assignment.get("bid_job_subject_ids") or []
    topics = assignment.get("topics")
    topic_subject_ids = (
        [s.subject_id for s in self._subjects_crud.list({"topics": {"$in": topics}})]
        if topics else []
    )

    if explicit_subject_ids or topic_subject_ids:
        subject_ids = list(dict.fromkeys(explicit_subject_ids + topic_subject_ids))
    else:
        subject_ids = [s.subject_id for s in self._subjects_crud.list()]

    bid_job = self._bidding_client.create_bid_job(
        bid_job_evaluator_id=assignment["bid_job_evaluator_id"],
        bid_job_subject_ids=subject_ids,
        # ... other bid_job_* fields, all with defaults
    )
    self._tasks_crud.update(task.task_id, {
        "task_metadata.bid_job_id": bid_job["bid_job_id"],
        "task_assignment_status": "bidding",
    })

    while True:
        task_results = self._bidding_client.get_task_results(bid_job["bid_job_id"])
        winner = next((r for r in task_results if r.get("task_type") == "bid_winner"), None)
        if winner is not None:
            self._tasks_crud.update(task.task_id, {"task_output": winner["task_result"], "task_assignment_status": "completed"})
            return
        time.sleep(self._bid_poll_interval)   # default 5s, configurable on TaskAssignmentService
```

Xchange never calls `submit_and_wait` itself in this mode — **Orcade does
the actual subject delivery** (its own `bid_request` and `bid_winner`
notifications, see Orcade's own delegate-system doc). Xchange's role is
purely: open the job, then poll until Orcade records a `bid_winner` result,
then copy that result into its own `task_output`.

If bid-job creation itself fails (e.g. Orcade unreachable, or
`bid_job_evaluator_id` missing), the task is marked `failed` immediately and
no polling loop starts. If creation succeeds but Orcade never produces a
`bid_winner` (e.g. a required subject never bids — see Orcade's own docs),
this task's `task_assignment_status` stays `"bidding"` forever; there is no
timeout. See [§7](07-bidding-mode.md) for the full request/response detail
and how to inspect an in-flight bid job directly on Orcade.

---
[← Previous: APIs](03-apis.md) · [Back to index](README.md) · [Next: Functions to write →](05-functions.md)
