[← Back to index](README.md)

# 6. Deployment & walkthrough

## 6.1 Configuration

All configuration is through environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `MONGO_URL` | **required** | MongoDB connection string for the registry |
| `GATEWAY_DB_NAME` | `xchange_gateway` | Database holding the `exchanges` collection ([§2.3](02-schema.md#23-storage)) |
| `PORT` | `5000` | HTTP listen port |
| `HEALTH_CHECK_INTERVAL` | `30` | Seconds between background health sweeps. `0` disables them ([§5.2](05-health-checks.md#52-when-probes-run)). |
| `PROXY_READ_TIMEOUT` | `300` | Read timeout, in seconds, for forwarded calls ([§3.3](03-apis.md#33-gateway-forwarding)) |
| `DISCOVERY_WORKERS` | `8` | Thread-pool size for discovery's subject fan-out ([§4.3](04-discovery.md#43-stage-2-subject-fan-out)) |

The gateway needs **none** of exchange-db's external-service variables
(`FUNCTION_REGISTRY_URL`, `SUBJECT_DELEGATE_URL`, `BIDDING_SERVICE_URL`,
...). It only ever talks to exchange-db instances and its own MongoDB.

## 6.2 Build & deploy

The image is built the same way as exchange-db's (`python:3.11-buster`,
`pip install -r requirements.txt`, `python3 main.py`):

```bash
cd jobs-gateway
docker build . -t 100.114.179.122:31280/agents/xchange-jobs-gateway:latest
docker push 100.114.179.122:31280/agents/xchange-jobs-gateway:latest

kubectl apply -f ../k8s/jobs-gateway.yaml
```

`k8s/jobs-gateway.yaml` creates, in the `exchanges` namespace alongside the
exchanges themselves:

- a `jobs-gateway` Deployment (1 replica, port `5000`), pointed at the same
  MongoDB server as `demo-exchange`
  (`registry-0.registries.svc.cluster.local:27017`) but its own
  `xchange_gateway` database;
- a `jobs-gateway-svc` NodePort Service on **`30741`**, next to
  `demo-exchange-svc` on `30740`.

Run a single replica. Every replica runs its own background health sweep.
Several replicas would still give correct results, since probes are
idempotent writes, but each exchange would be probed once per replica per
interval.

Running locally:

```bash
cd jobs-gateway
pip install -r requirements.txt
MONGO_URL=mongodb://localhost:27017 PORT=5001 python3 main.py
```

## 6.3 End-to-end walkthrough

This assumes `demo-exchange` is deployed from `k8s/deploy.yaml` and the
gateway from `k8s/jobs-gateway.yaml`. Calls go to the gateway's NodePort
(`$GW`, e.g. `http://<node-ip>:30741`). Note that **`exchange_api_url` must
be reachable from the gateway pod**, not from your laptop, so in-cluster
service DNS is the right choice here.

**1. Register the exchange.**

```bash
curl -X POST $GW/exchanges \
  -H "Content-Type: application/json" \
  -d '{
    "exchange_id": "demo-exchange",
    "exchange_api_url": "http://demo-exchange-svc.exchanges.svc.cluster.local:5000",
    "exchange_name": "Demo exchange",
    "exchange_tags": ["nlp", "public"]
  }'
```
→ `201`, `exchange_status: "healthy"`.

**2. Add a subject to it through the gateway.**

```bash
curl -X POST $GW/exchanges/demo-exchange/api/subjects \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "agent-summarizer-01",
    "subject_capabilities": {"max_doc_tokens": 50000},
    "topics": ["summarization", "nlp"]
  }'
```
→ `201`, forwarded from exchange-db's `POST /subjects`.

**3. Discover where summarization work can go.**

```bash
curl -X POST $GW/discover \
  -H "Content-Type: application/json" \
  -d '{"status": "healthy", "subject_topics": ["summarization"]}'
```
→ `demo-exchange` with `matching_subject_ids: ["agent-summarizer-01"]`.

**4. Submit a task to the chosen exchange and subject.**

```bash
curl -X POST $GW/exchanges/demo-exchange/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_assignment_type": "direct",
    "task_data": {"instruction": "summarize this document", "doc_url": "https://storage.example.com/report.pdf"},
    "task_metadata": {"task_assignment": {"subject_id": "agent-summarizer-01"}}
  }'
```
→ `201` with the new `task_id`.

**5. Poll for the result.**

```bash
curl $GW/exchanges/demo-exchange/api/tasks/<task_id>/output
```
→ `task_assignment_status` moves from `pending` to `completed` (or
`failed`), exactly as described in
[Exchange System §3.4](../exchange-system/03-apis.md#34-how-to-read-task-output).

**Adding another exchange** is just another deployment (copy
`k8s/deploy.yaml` with a new name, `EXCHANGE_ID` and `nodePort`) plus another
`POST /exchanges`. Steps 3–5 then automatically consider it.

---
[← Previous: Health checks](05-health-checks.md) · [Back to index](README.md)
