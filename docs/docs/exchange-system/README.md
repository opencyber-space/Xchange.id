# Exchange System (Xchange)

Xchange runs one **exchange** per deployment (`EXCHANGE_ID`, e.g.
`demo-exchange`) — a task board that accepts **tasks**, decides which of its
registered **subjects** (agents) should do the work, hands the task off, and
records the result. Unlike Orcade (which always runs a fixed multi-subject
bidding round), Xchange supports four different **assignment modes** per
task, chosen by the caller at submission time — from a pinned direct
assignment all the way up to delegating the whole selection process to
Orcade's bidding system. All communication with a subject happens through
the same external **delegate system** used by Orcade, and pluggable
selection/evaluation logic is delegated to functions hosted in the same
external **function registry**.

Source of truth for everything in this documentation set:

| File | Responsibility |
|---|---|
| `exchange-db/core/schema.py` | `ExchangeTasks`, `ExchangeSubjects` dataclasses |
| `exchange-db/core/crud.py` | MongoDB persistence for the two collections above, in DB `exchange_{EXCHANGE_ID}` |
| `exchange-db/core/task_assignment.py` | `TaskAssignmentService` — the orchestration logic for all four assignment modes |
| `exchange-db/core/apis.py` | Flask REST API (`app`, mounted via `main.py` / `run_server()`) |
| `exchange-db/core/functions.py` | `FunctionCaller` — thin wrapper for invoking selector/evaluator functions |
| `exchange-db/core/agents_functions/` | Low-level client for the function registry (`AgentFunctions`, `FunctionsRegistryClient`, `FunctionCaller`) — copied as-is from Orcade |
| `exchange-db/core/subject_task.py` | `SubjectTask` — client for the delegate system — copied as-is from Orcade |
| `exchange-db/core/bidding_client.py` | `BiddingClient` — client for Orcade's own bid-job REST API, used only by the `bidding` assignment mode |

## Contents

1. [Concepts](01-concepts.md) — actors, the four assignment modes, and how they compare
2. [Schema](02-schema.md) — `ExchangeTasks`, `ExchangeSubjects` field references, sample documents, storage
3. [APIs](03-apis.md) — full REST reference: submitting tasks, reading output, subject CRUD
4. [Assignment modes](04-assignment-modes.md) — step-by-step orchestration for `direct` / `function` / `open` / `bidding`
5. [Functions to write](05-functions.md) — selector-function and task-evaluation-function contracts, with reference implementations
6. [Delegate system](06-delegate-system.md) — how a task is delivered to a subject agent
7. [Bidding mode integration](07-bidding-mode.md) — how the `bidding` mode drives Orcade's own bid-job API

## Related

- [Jobs Gateway](../jobs-gateway/README.md): registry, discovery and a single front door for many exchange-db instances
