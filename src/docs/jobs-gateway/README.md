# Jobs Gateway

One Xchange deployment is one exchange: an `exchange-db` instance with its
own `EXCHANGE_ID`, its own MongoDB database and its own subjects (see the
[Exchange System docs](../exchange-system/README.md)). An exchange-db
instance knows nothing about any other exchange. The **jobs gateway** is the
layer that sits in front of all of them:

- **Registry.** Each exchange-db instance is registered once, under its
  `EXCHANGE_ID`, with the base URL it can be reached at, plus tags and
  free-form metadata.
- **Discovery.** Callers find exchanges by registry fields (tags, status,
  any raw Mongo filter), and optionally by what the exchanges' **subjects**
  look like. The gateway sends the subject question to every candidate
  exchange's own `/subjects/query` at the same time and returns only the
  exchanges with matches.
- **Gateway.** Any exchange-db API call can be sent to
  `/exchanges/{exchange_id}/api/<path>`. The gateway looks up the exchange's
  URL and forwards the request unchanged, so callers only need to know an
  `exchange_id`, never a host or port.
- **Health checks.** The gateway periodically probes every registered
  exchange and records `healthy` / `unreachable` on its registry entry, so
  discovery can skip exchanges that are down.

The gateway never reads or writes an exchange's MongoDB directly. Everything
it knows about an exchange's subjects or tasks comes from that exchange's
own REST API.

Source of truth for everything in this documentation set:

| File | Responsibility |
|---|---|
| `jobs-gateway/core/schema.py` | `ExchangeEntry` dataclass and the `exchange_status` constants |
| `jobs-gateway/core/crud.py` | MongoDB persistence for registry entries, in DB `GATEWAY_DB_NAME` (default `xchange_gateway`) |
| `jobs-gateway/core/exchange_client.py` | `ExchangeClient`: HTTP client for exchange-db (health probe, subject query, request forwarding) |
| `jobs-gateway/core/discovery.py` | `DiscoveryService`: registry filtering plus parallel subject fan-out |
| `jobs-gateway/core/health.py` | `HealthChecker`: on-demand and background health checks |
| `jobs-gateway/core/apis.py` | Flask REST API (`app`, started via `main.py` / `run_server()`) |
| `k8s/jobs-gateway.yaml` | Kubernetes Deployment + NodePort Service |

## Contents

1. [Concepts](01-concepts.md): what the gateway is for, how it relates to exchange-db, and what it deliberately doesn't do
2. [Schema](02-schema.md): `ExchangeEntry` field reference, sample document, storage
3. [APIs](03-apis.md): full REST reference for registry, health-check and gateway forwarding
4. [Discovery](04-discovery.md): `POST /discover` in detail, with registry filters, subject fan-out and the response shape
5. [Health checks](05-health-checks.md): how an exchange is probed and what `exchange_status` means
6. [Deployment & walkthrough](06-deployment.md): environment variables, Kubernetes, and an end-to-end example
