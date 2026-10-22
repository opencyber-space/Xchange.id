[← Back to index](README.md)

# 1. Concepts

## 1.1 Actors

- **Exchange** (`EXCHANGE_ID`) — one Xchange deployment is one exchange. It
  owns its own MongoDB database (`exchange_{EXCHANGE_ID}`, see
  [§2.4](02-schema.md#24-storage)) and its own set of subjects. There is no
  cross-exchange query surface — "all subjects in the exchange" always means
  "every `ExchangeSubjects` document in this deployment's database".
- **Task** (`ExchangeTasks`) — a unit of work submitted to the exchange. Its
  `task_assignment_type` picks one of four orchestration strategies
  ([§1.2](#12-the-four-assignment-modes)); its `task_metadata.task_assignment`
  sub-object carries the parameters that strategy needs (which subject, which
  function, which bid-job fields, ...).
- **Subject** (`ExchangeSubjects`) — a registered agent that can receive
  tasks. Subjects are plain CRUD records ([§3.3](03-apis.md#subjects)) — there
  is no separate "join the exchange" workflow beyond creating the record.
  A subject's `task_evaluation_function` field is only consulted by the
  `open` assignment mode.
- **Selector function** (`function` mode only) — an external function,
  resolved by `function_id`, invoked once with the task and the full subject
  list; it must return a `selected_subject_id`. See
  [§5.1](05-functions.md#51-selector-function-function-mode).
- **Task evaluation function** (`open` mode only) — each subject carries its
  own, via `ExchangeSubjects.task_evaluation_function`. Called per-subject,
  in order, until one accepts. See
  [§5.2](05-functions.md#52-task-evaluation-function-open-mode).
- **Delegate system** (`SUBJECT_DELEGATE_URL`) — the same external service
  Orcade uses to reach a live subject and get a response back
  (`SubjectTask.submit_and_wait`, see [§6](06-delegate-system.md)). Xchange
  never talks to a subject directly.
- **Function registry** (`FUNCTION_REGISTRY_URL`) — the same external
  function-hosting service Orcade uses. Xchange resolves selector /
  task-evaluation `function_id`s against it via `FunctionCaller` (see
  [§5](05-functions.md)), reusing the exact same `agents_functions` client
  code as Orcade.
- **Orcade / bidding system** (`BIDDING_SERVICE_URL`) — used only by the
  `bidding` assignment mode. Xchange acts as a *creator* against Orcade's own
  `/bid-jobs` API — see [§7](07-bidding-mode.md).

## 1.2 The four assignment modes

Set on submission via `task_assignment_type`:

| Mode | Selection | Assignment timing | Submission timing |
|---|---|---|---|
| `direct` | Caller names the `subject_id` up front. No selection logic runs at all. | N/A (fixed) | Background thread |
| `function` | A single selector function picks one subject from the full subject list. | Synchronous (blocks the `POST /tasks` call) | Background thread |
| `open` | Each subject's own `task_evaluation_function` is asked in turn; first `"accepted"` wins. | Entirely on a background thread | Same background thread (sequential, not parallel) |
| `bidding` | Delegated wholesale to Orcade: a bid job is opened for the subject set and Orcade's own evaluator picks the winner. | Entirely on a background thread | Handled by Orcade, not Xchange; Xchange only polls for the outcome |

```
 direct:    POST /tasks ──► persist task ─┬─► return 201 to caller
                                           └─► [thread] submit_and_wait(subject_id) ──► save task_output

 function:  POST /tasks ──► persist task ──► call selector function (blocking)
                                           ├─► return 201 to caller (status="assigned")
                                           └─► [thread] submit_and_wait(selected_subject_id) ──► save task_output

 open:      POST /tasks ──► persist task ──► return 201 to caller
                                           └─► [thread] for each subject:
                                                          call subject.task_evaluation_function
                                                          if "accepted" → submit_and_wait(subject_id) ──► save task_output; stop
                                                          if none accept → status="rejected"

 bidding:   POST /tasks ──► persist task ──► return 201 to caller
                                           └─► [thread] create Orcade bid job
                                                          poll Orcade for a "bid_winner" task-result
                                                          save it as task_output
```

Key behavioral notes:

- **`POST /tasks` always returns as soon as the task is persisted and (for
  `function` mode only) a subject has been synchronously selected.** It never
  waits for the subject's actual response — that always happens on a
  background thread, for all four modes. Poll
  `GET /tasks/{task_id}` or `GET /tasks/{task_id}/output`
  ([§3.4](03-apis.md#34-how-to-read-task-output)) to find out what happened.
- **`function` mode is the only mode with a synchronous step.** Selecting the
  subject happens inline inside the request handler; if the selector function
  raises or doesn't return `selected_subject_id`, `POST /tasks` itself fails
  (`400`) and the task is marked `failed` — nothing is submitted to any
  subject.
- **`open` mode evaluates subjects sequentially, not in parallel, and stops
  at the first acceptance.** Subject order is whatever
  `ExchangeSubjectsCRUD.list()` returns (MongoDB's natural document order —
  not otherwise guaranteed). If a subject's `task_evaluation_function` call
  raises, that subject is treated as a non-accept (logged and skipped) rather
  than failing the whole task.
- **`bidding` mode has no timeout.** It polls Orcade's
  `/bid-jobs/{id}/task-results` every `bid_poll_interval` seconds (default
  5s) forever, until a `"bid_winner"` entry shows up. If Orcade's own
  bidding never resolves (e.g. a required subject never bids), the Xchange
  task sits in `task_assignment_status="bidding"` indefinitely.
- **`task_assignment_status` values you'll observe:** `pending` (just
  submitted, only briefly before a mode-specific handler updates it),
  `assigned` (function/open mode has picked a subject, submission thread not
  yet finished), `bidding` (bid job created, waiting on Orcade),
  `completed` (subject responded, see `task_output`), `failed` (an
  exception occurred — see `task_output.error`), `rejected` (`open` mode
  exhausted every subject with no acceptance).

---
[← Back to index](README.md) · [Next: Schema →](02-schema.md)
