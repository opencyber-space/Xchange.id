import os
import logging
from datetime import datetime
from typing import Any, Dict

from flask import Flask, Response, request, jsonify

from .crud import ExchangeRegistryCRUD
from .discovery import DiscoveryService, build_registry_query, build_subject_query
from .exchange_client import ExchangeClient
from .health import HealthChecker
from .schema import STATUS_HEALTHY, STATUS_UNKNOWN, ExchangeEntry

logger = logging.getLogger(__name__)

registry_crud = ExchangeRegistryCRUD()
exchange_client = ExchangeClient(
    timeout=(10, int(os.getenv("PROXY_READ_TIMEOUT", "300"))),
)
health_checker = HealthChecker(
    registry_crud=registry_crud,
    exchange_client=exchange_client,
    interval=float(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
)
discovery_service = DiscoveryService(
    registry_crud=registry_crud,
    exchange_client=exchange_client,
    num_workers=int(os.getenv("DISCOVERY_WORKERS", "8")),
)

# Managed by the gateway itself; ignored if a caller sends them.
SERVER_MANAGED_FIELDS = (
    "exchange_status",
    "registration_time",
    "last_health_check_time",
    "last_health_check_error",
)

app = Flask(__name__)


def _json_response(ok: bool, data: Any = None, error: str = None, status: int = 200):
    payload: Dict[str, Any] = {"ok": ok}
    if ok:
        if data is not None:
            payload["data"] = data
    else:
        payload["error"] = error or "unknown_error"
    return jsonify(payload), status


# ------------------ REGISTRY ------------------

@app.post("/exchanges")
def register_exchange():
    body = request.get_json(silent=True) or {}
    try:
        exchange_id = body["exchange_id"]
        exchange_api_url = body["exchange_api_url"]
    except KeyError as e:
        return _json_response(False, error=f"Missing required field: {e}", status=400)

    if registry_crud.get(exchange_id) is not None:
        return _json_response(False, error="exchange already registered", status=409)

    entry = ExchangeEntry(
        exchange_id=exchange_id,
        exchange_api_url=exchange_api_url.rstrip("/"),
        exchange_name=body.get("exchange_name", ""),
        exchange_description=body.get("exchange_description", ""),
        exchange_tags=body.get("exchange_tags", []),
        exchange_metadata=body.get("exchange_metadata", {}),
        registration_time=datetime.utcnow(),
    )

    if not body.get("skip_health_check", False):
        try:
            exchange_client.check_health(entry.exchange_api_url)
        except Exception as e:
            return _json_response(
                False,
                error=f"exchange not reachable at {entry.exchange_api_url}: {e}",
                status=400,
            )
        entry.exchange_status = STATUS_HEALTHY
        entry.last_health_check_time = datetime.utcnow()

    try:
        registry_crud.create(entry)
    except Exception as e:
        logger.exception("register_exchange failed")
        return _json_response(False, error=str(e), status=500)

    return _json_response(True, entry.to_dict(), status=201)


@app.get("/exchanges/<exchange_id>")
def get_exchange(exchange_id: str):
    entry = registry_crud.get(exchange_id)
    if entry is None:
        return _json_response(False, error="exchange not found", status=404)
    return _json_response(True, entry.to_dict())


@app.put("/exchanges/<exchange_id>")
@app.patch("/exchanges/<exchange_id>")
def update_exchange(exchange_id: str):
    body = request.get_json(silent=True) or {}
    if "exchange_id" in body and body["exchange_id"] != exchange_id:
        return _json_response(False, error="exchange_id cannot be changed", status=400)

    existing = registry_crud.get(exchange_id)
    if existing is None:
        return _json_response(False, error="exchange not found", status=404)

    updates = {k: v for k, v in body.items() if k not in SERVER_MANAGED_FIELDS and k != "exchange_id"}
    if "exchange_api_url" in updates:
        updates["exchange_api_url"] = updates["exchange_api_url"].rstrip("/")
        if updates["exchange_api_url"] != existing.exchange_api_url:
            # The old health result says nothing about the new URL.
            updates["exchange_status"] = STATUS_UNKNOWN

    try:
        if updates:
            registry_crud.update(exchange_id, updates)
        return _json_response(True, registry_crud.get(exchange_id).to_dict())
    except Exception as e:
        logger.exception("update_exchange failed")
        return _json_response(False, error=str(e), status=500)


@app.delete("/exchanges/<exchange_id>")
def delete_exchange(exchange_id: str):
    try:
        deleted = registry_crud.delete(exchange_id)
        if not deleted:
            return _json_response(False, error="exchange not found", status=404)
        return _json_response(True, {"deleted": True})
    except Exception as e:
        logger.exception("delete_exchange failed")
        return _json_response(False, error=str(e), status=500)


@app.post("/exchanges/query")
def query_exchanges():
    query = request.get_json(silent=True) or {}
    try:
        entries = registry_crud.list(query)
        return _json_response(True, [e.to_dict() for e in entries])
    except Exception as e:
        logger.exception("query_exchanges failed")
        return _json_response(False, error=str(e), status=400)


@app.post("/exchanges/<exchange_id>/health-check")
def check_exchange_health(exchange_id: str):
    entry = registry_crud.get(exchange_id)
    if entry is None:
        return _json_response(False, error="exchange not found", status=404)
    return _json_response(True, health_checker.check(entry).to_dict())


# ------------------ DISCOVERY ------------------

@app.post("/discover")
def discover():
    body = request.get_json(silent=True) or {}
    try:
        result = discovery_service.discover(
            registry_query=build_registry_query(
                query=body.get("query"),
                tags=body.get("tags"),
                status=body.get("status"),
            ),
            subject_query=build_subject_query(
                subject_query=body.get("subject_query"),
                subject_topics=body.get("subject_topics"),
            ),
        )
        return _json_response(True, result)
    except Exception as e:
        logger.exception("discover failed")
        return _json_response(False, error=str(e), status=400)


# ------------------ GATEWAY ------------------

@app.route(
    "/exchanges/<exchange_id>/api/<path:subpath>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
def forward_to_exchange(exchange_id: str, subpath: str):
    entry = registry_crud.get(exchange_id)
    if entry is None:
        return _json_response(False, error="exchange not found", status=404)

    try:
        resp = exchange_client.forward(
            entry.exchange_api_url,
            request.method,
            subpath,
            params=list(request.args.items(multi=True)),
            body=request.get_data() or None,
            content_type=request.headers.get("Content-Type"),
        )
    except Exception as e:
        logger.exception(f"forward to exchange '{exchange_id}' failed")
        return _json_response(
            False, error=f"exchange '{exchange_id}' unreachable: {e}", status=502
        )

    return Response(
        resp.content,
        status=resp.status_code,
        content_type=resp.headers.get("Content-Type", "application/json"),
    )


@app.get("/health")
def health():
    return _json_response(True, {"status": "ok"})


def run_server():
    health_checker.start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
