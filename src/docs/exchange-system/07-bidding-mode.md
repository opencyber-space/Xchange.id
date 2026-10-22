[← Back to index](README.md)

# 7. Bidding mode integration

`bidding` mode makes Xchange act as a **creator** against Orcade's own
`/bid-jobs` REST API (see Orcade's
[APIs doc](../../../orcade/docs/bidding-system/03-apis.md)), via a small
client — `BiddingClient` (`exchange-db/core/bidding_client.py`) — rather
than reimplementing any bidding/evaluation logic locally. Everything about
*how* a bid job actually resolves (subject eligibility, PQT rejection,
evaluator semantics, the `bid_request`/`bid_winner` delegate notifications)
is Orcade's behavior, documented in full in
[Orcade's own docs](../../../orcade/docs/bidding-system/README.md) — this
page only covers the Xchange-side glue.

## 7.1 `BiddingClient`

```python
class BiddingClient:
    def __init__(self, *, base_url=None, timeout=(10, 30)):
        self.base_url = (base_url or os.environ["BIDDING_SERVICE_URL"]).rstrip("/")
        ...

    def create_bid_job(self, **kwargs) -> dict: ...      # POST /bid-jobs
    def get_bid_job(self, bid_job_id) -> dict: ...        # GET /bid-jobs/{id}
    def get_bids(self, bid_job_id) -> list: ...           # GET /bid-jobs/{id}/bids
    def get_task_results(self, bid_job_id) -> list: ...   # GET /bid-jobs/{id}/task-results
```

Base URL comes from `BIDDING_SERVICE_URL` (in the k8s manifest, Orcade's
in-cluster service DNS). Each method unwraps Orcade's `{"ok": ..., "data"/"error": ...}`
envelope itself and raises `RuntimeError(error)` on `"ok": false`, or lets
`requests`' own `HTTPError` propagate on a transport-level failure (non-2xx,
timeout, connection error) — either way, the caller in
`TaskAssignmentService` catches `Exception` broadly, so both failure shapes
are handled identically.

## 7.2 Creating the bid job

From `_run_bidding()`, on the background thread started for the task:

```python
bid_job = self._bidding_client.create_bid_job(
    bid_job_metadata=assignment.get("bid_job_metadata", {}),
    bid_job_description=assignment.get("bid_job_description", {}),
    bid_job_name=assignment.get("bid_job_name", {}),
    bid_job_evaluator_id=assignment["bid_job_evaluator_id"],
    bid_job_pqt_id=assignment.get("bid_job_pqt_id", ""),
    bid_job_tie_id=assignment.get("bid_job_tie_id", ""),
    bid_job_creator_id=assignment.get("bid_job_creator_id", ""),
    bid_job_subject_ids=subject_ids,
)
```

`subject_ids` is resolved as follows:

1. Start from `assignment["bid_job_subject_ids"]` — an explicit list — if
   given (the "manually specified" case); otherwise an empty list.
2. If `assignment["topics"]` is also given, resolve it to
   `[s.subject_id for s in ExchangeSubjectsCRUD.list({"topics": {"$in": topics}})]`
   — every subject whose own `topics` field
   ([§2.2](02-schema.md#22-exchangesubjects)) contains **any** of the
   requested topics — and take the **union** (deduplicated,
   order-preserving) with the explicit list from step 1. Neither field takes
   priority over the other; specifying both adds their results together.
3. If both `bid_job_subject_ids` and `topics` were omitted entirely, fall
   back to every subject currently registered in this exchange
   (`ExchangeSubjectsCRUD.list()` with no filter).

Note this list is captured once, at bid-job creation time — however it was
resolved — a subject added (or re-tagged) afterwards is not retroactively
added to an already-created bid job (Orcade's `bid_job_subject_ids` is
fixed at creation, see Orcade's
[concepts doc](../../../orcade/docs/bidding-system/01-concepts.md#11-actors)).

On success, the returned `bid_job["bid_job_id"]` is written back onto the
Xchange task immediately, so it can be cross-referenced or queried directly
against Orcade later:

```python
self._tasks_crud.update(task.task_id, {
    "task_metadata.bid_job_id": bid_job["bid_job_id"],
    "task_assignment_status": "bidding",
})
```

If `create_bid_job` itself raises (network failure, or Orcade rejects it —
e.g. `bid_job_evaluator_id` required but this docstring already made it
required on the Xchange side too), the task is marked `failed` and no
polling ever starts.

## 7.2a Open mode

With `bid_job_mode: "open"`, `_run_bidding` skips subject resolution entirely
and sends `bid_job_subject_ids=[]` together with `bid_job_mode`,
`bid_job_max_subjects`, `bid_job_max_time`, and `bid_job_tags`. Orcade does
not notify anyone on creation; subjects discover the job by tag
(`GET /bid-jobs/by-tags` on Orcade) and apply by posting a bid.

The poller checks for two terminal conditions each cycle:

- a `bid_winner` task-result exists → `completed`, as in closed mode;
- the job has `bid_job_status == "closed"` **and** `GET /bid-jobs/{id}/bids`
  is empty → `rejected` with `"no subject applied to the bid job"`. Bids are
  persisted before a subject claims its slot, so an empty bid list on a
  closed job means no one ever applied.

A closed job that has applicants but no `bid_winner` (for example, the
evaluator failed) still polls indefinitely, as in closed mode.

## 7.2b Mixed mode

`bid_job_mode: "mixed"` needs no special casing in `_run_bidding` — the
subject-pool-resolution branch only skips for `bid_job_mode == "open"`, and
every other mode (including `"mixed"`) goes through the exact same
`bid_job_subject_ids` / `topics` union logic as `closed` (§7.2). The only
difference happens entirely on Orcade's side: Orcade requires a non-empty
roster for mixed mode (empty → create-job failure → Xchange task marked
`failed`, same as any other Orcade-side rejection), sends `bid_request` to
every named subject just like closed mode, *and* additionally tags the job
with `subject::<subject_id>` for each one, so a subject can also find it via
`GET /bid-jobs/by-tags` instead of relying on the push notification. Xchange
itself never queries by tag — that lookup is something a subject does
against Orcade directly, outside Xchange's own flow. `bid_job_max_subjects`
/ `bid_job_max_time` do not apply to mixed mode; if set, Orcade rejects the
job the same way it would for `closed`. Polling behaves exactly like closed
mode too — no early "no applicants" exit, since mixed mode has no open/closed
application window.

## 7.3 Polling for the result

```python
while True:
    task_results = self._bidding_client.get_task_results(bid_job_id)
    winner = next((r for r in task_results if r.get("task_type") == "bid_winner"), None)
    if winner is not None:
        self._tasks_crud.update(task.task_id, {"task_output": winner["task_result"], "task_assignment_status": "completed"})
        return
    time.sleep(self._bid_poll_interval)
```

`get_task_results` maps to Orcade's `GET /bid-jobs/{id}/task-results`, which
returns **every** delegate round-trip for the job — both `bid_request` (one
per subject, sent immediately on job creation) and `bid_winner` (one, sent
once Orcade's evaluator has resolved a winner). Xchange only cares about the
`bid_winner` entry; `winner["task_result"]` is Orcade's
`BidTaskResult.task_result` — i.e. **the winning subject's raw response to
the `bid_winner` delegate notification**, not the evaluator's own
`result_data` output. If you need the evaluator's `result_data` (agreed
price, rationale, etc.) in `task_output` too, either have the evaluator
function embed it into what gets sent to the subject (so it round-trips
back through the subject's response), or extend `_run_bidding` to also fetch
it — Orcade doesn't expose the evaluator's raw output via any endpoint, only
via what it forwards to the winning subject (see Orcade's
[delegate-system doc, §5.3](../../../orcade/docs/bidding-system/05-delegate-system.md#53-bid_winner--sent-after-evaluation)).

**Failure/liveness notes:**

- A transient error from `get_task_results` (Orcade briefly unreachable)
  does **not** fail the task — it's logged and the loop just retries after
  `bid_poll_interval` seconds (default 5s, set via
  `TaskAssignmentService(bid_poll_interval=...)`).
- There is **no timeout** on the loop itself. If the bid job never produces
  a `bid_winner` (per Orcade's own rules: evaluation only fires once *every*
  subject in `bid_job_subject_ids` has bid — see Orcade's
  [concepts doc](../../../orcade/docs/bidding-system/01-concepts.md#12-lifecycle-of-a-bid-job)),
  this Xchange task sits in `task_assignment_status="bidding"` forever. To
  debug a stuck job, use the `bid_job_id` written to
  `task_metadata.bid_job_id` and query Orcade directly:
  `GET {BIDDING_SERVICE_URL}/bid-jobs/{bid_job_id}/bids` to see who has/hasn't
  bid yet.

---
[← Previous: Delegate system](06-delegate-system.md) · [Back to index](README.md)
