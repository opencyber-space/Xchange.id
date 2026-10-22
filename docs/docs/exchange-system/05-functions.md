[← Back to index](README.md)

# 5. Functions to write (selector & task-evaluation)

Like Orcade's PQT/evaluator functions, these are **not code inside
Xchange**. They are entries in the same external function registry
(`FUNCTION_REGISTRY_URL`), referenced purely by `function_id` string, and
resolved/invoked through the exact same client code Orcade uses:
`FunctionCaller` (`exchange-db/core/functions.py`) →
`AgentFunctions` (`exchange-db/core/agents_functions/__init__.py`), which
supports the same three execution modes per `FunctionEntry` — **external**
(plain HTTP `POST`), **stateful** (long-lived deployment, cached per
`function_id` for the process lifetime), and **stateless** (one-off
registry-managed job). See Orcade's own
[functions doc, §4.1](https://openarcade-internal.pages.dev/bids-system/04-functions/#41-authoring-format-aiosv1policyrule)
for the full `AIOSv1PolicyRule` authoring contract (`__init__(rule_id,
settings, parameters)` / `eval(parameters, input_data, context)`) — it
applies unchanged here, since it's the same registry and the same client
code.

Xchange uses this mechanism for two different kinds of function, one per
assignment mode:

## 5.1 Selector function (`function` mode)

**Purpose:** given a task and the full set of subjects in the exchange,
pick exactly one subject to do the work.

**When it's called:** once per task, **synchronously**, inline inside
`POST /tasks`, only for `task_assignment_type: "function"`. See
[§4.2](04-assignment-modes.md#42-function-mode).

**Input contract:**

```json
{
  "task_data": { "...": "the submitted task's task_data, verbatim" },
  "subjects": [ { "...": "full ExchangeSubjects.to_dict()" }, "... every subject in the exchange" ]
}
```

`parameters` from `task_metadata.task_assignment.parameters` is also
forwarded via `FunctionCaller.call(..., parameters=...)` — for a **stateful**
or **stateless** function this arrives as both the `parameters` argument to
`eval()` *and* merged into `input_data["parameters"]`; for an **external**
function it is silently dropped (the HTTP `POST` body is `input_data` only,
with no `parameters` key added) — same caveat Orcade documents for its own
evaluator calls.

**Output contract:**

| Key | Type | Required | Meaning |
|---|---|---|---|
| `selected_subject_id` | `string` | **yes** | Must be truthy. If missing/falsy, `TaskAssignmentService` raises, `POST /tasks` returns `400`, and the task is marked `failed` — **no subject is ever notified**. There is no validation that this ID actually matches one of the subjects passed in `subjects`; an invalid ID simply fails later at the delegate-system call (`_submit_and_save`), marking the task `failed` at that point instead. |

**Example input:**

```json
{
  "task_data": {"instruction": "summarize this document", "doc_url": "https://storage.example.com/report.pdf"},
  "subjects": [
    {
      "subject_id": "agent-summarizer-01",
      "subject_metadata": {"owner": "team-nlp"},
      "task_evaluation_function": "",
      "subject_capabilities": {"max_doc_tokens": 50000}
    },
    {
      "subject_id": "agent-summarizer-02",
      "subject_metadata": {"owner": "team-nlp"},
      "task_evaluation_function": "",
      "subject_capabilities": {"max_doc_tokens": 200000}
    }
  ]
}
```

**Example output:**

```json
{ "selected_subject_id": "agent-summarizer-02" }
```

**Reference implementation** (`AIOSv1PolicyRule`, picks the subject with the
largest declared capacity, for a stateful or stateless function):

```python
import logging


class AIOSv1PolicyRule:

    def __init__(self, rule_id, settings, parameters):
        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

    def eval(self, parameters, input_data, context):
        logging.info("selector input: {}".format(input_data))

        subjects = input_data["subjects"]
        best = max(subjects, key=lambda s: s.get("subject_capabilities", {}).get("max_doc_tokens", 0))

        return {"selected_subject_id": best["subject_id"]}
```

**Alternative reference implementation** (external HTTP mode,
`is_external=True`):

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/")
def select():
    payload = request.get_json()
    subjects = payload["subjects"]

    best = max(subjects, key=lambda s: s.get("subject_capabilities", {}).get("max_doc_tokens", 0))

    return jsonify({"data": {"selected_subject_id": best["subject_id"]}})
```

## 5.2 Task evaluation function (`open` mode)

**Purpose:** ask a *single* subject whether it will accept a given task.
Unlike the selector function, this is per-subject: it is stored on the
subject itself (`ExchangeSubjects.task_evaluation_function`), not on the
task.

**When it's called:** once per candidate subject, in sequence, entirely on
a background thread, only for `task_assignment_type: "open"`. Stops at the
first `"accepted"` response — later subjects in the list are never asked.
Subjects with an empty `task_evaluation_function` are skipped and never
called at all. See [§4.3](04-assignment-modes.md#43-open-mode).

**Input contract:**

```json
{
  "task_data": { "...": "the submitted task's task_data, verbatim" },
  "subject": { "...": "full ExchangeSubjects.to_dict() for just this one subject" }
}
```

No `parameters` are passed for this call (`FunctionCaller.call()` is invoked
with no `parameters=` kwarg, so it defaults to `None`).

**Output contract:**

| Key | Type | Required | Meaning |
|---|---|---|---|
| `status` | `string` | **yes** (compared exactly) | `"accepted"` → this subject wins; the task is submitted to it and evaluation stops. Anything else (including missing) → treated as a decline, next subject is tried. |
| *(anything else)* | any | no | Ignored by Xchange today; free to add a `reason` field for your own logging. |

**Example input:**

```json
{
  "task_data": {"instruction": "summarize this document", "doc_url": "https://storage.example.com/report.pdf"},
  "subject": {
    "subject_id": "agent-summarizer-01",
    "subject_metadata": {"owner": "team-nlp"},
    "task_evaluation_function": "accepts-if-capacity:1.0-stable",
    "subject_capabilities": {"max_doc_tokens": 50000}
  }
}
```

**Example output (accept):**
```json
{ "status": "accepted" }
```

**Example output (reject):**
```json
{ "status": "rejected", "reason": "at capacity" }
```

**Reference implementation** (`AIOSv1PolicyRule`, accepts if the subject's
own declared capacity covers the task, for a stateful or stateless
function):

```python
import logging


class AIOSv1PolicyRule:

    def __init__(self, rule_id, settings, parameters):
        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

    def eval(self, parameters, input_data, context):
        logging.info("task evaluation input: {}".format(input_data))

        subject = input_data["subject"]
        task_data = input_data["task_data"]

        capacity = subject.get("subject_capabilities", {}).get("max_doc_tokens", 0)
        required = task_data.get("estimated_tokens", 0)

        if required > capacity:
            return {"status": "rejected", "reason": f"requires {required} tokens, capacity is {capacity}"}

        return {"status": "accepted"}
```

**Alternative reference implementation** (external HTTP mode,
`is_external=True`):

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/")
def evaluate():
    payload = request.get_json()
    subject = payload["subject"]
    task_data = payload["task_data"]

    capacity = subject.get("subject_capabilities", {}).get("max_doc_tokens", 0)
    required = task_data.get("estimated_tokens", 0)

    if required > capacity:
        return jsonify({"data": {"status": "rejected", "reason": f"requires {required} tokens, capacity is {capacity}"}})

    return jsonify({"data": {"status": "accepted"}})
```

## 5.3 Registering a function

Same as Orcade: whatever you write must already exist in the function
registry under a `function_id` *before* it's referenced (as
`task_metadata.task_assignment.function_id` for `function` mode, or as
`ExchangeSubjects.task_evaluation_function` for `open` mode).
`AgentFunctions.add()` is called automatically, lazily, the first time
`FunctionCaller.call()` sees a given `function_id`, and raises `ValueError`
if the registry has nothing registered under it — for `function` mode this
surfaces as the `400` on `POST /tasks`; for `open` mode it's caught per-subject
and logged, treated as that subject declining (see
[§4.3](04-assignment-modes.md#43-open-mode)). Registering the function itself
happens against the function registry service directly, outside Xchange's
own API surface — identical to how it's done for Orcade.

---
[← Previous: Assignment modes](04-assignment-modes.md) · [Back to index](README.md) · [Next: Delegate system →](06-delegate-system.md)
