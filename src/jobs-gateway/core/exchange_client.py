import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# exchange-db has no dedicated health route. Fetching a task ID that can never
# exist makes it run a real Mongo lookup and answer 404 {"ok": false, ...};
# getting that envelope back proves both the Flask app and its DB are up.
HEALTH_PROBE_TASK_ID = "__jobs_gateway_health_probe__"


class ExchangeClient:
    def __init__(
        self,
        *,
        timeout: Tuple[int, int] = (10, 300),
        health_timeout: Tuple[int, int] = (5, 10),
        discovery_timeout: Tuple[int, int] = (5, 30),
    ):
        self.timeout = timeout
        self.health_timeout = health_timeout
        self.discovery_timeout = discovery_timeout
        self.session = requests.Session()

    def check_health(self, base_url: str) -> None:
        url = f"{base_url.rstrip('/')}/tasks/{HEALTH_PROBE_TASK_ID}"
        resp = self.session.get(url, timeout=self.health_timeout)
        if resp.status_code in (200, 404):
            try:
                body = resp.json()
            except ValueError:
                body = None
            if isinstance(body, dict) and "ok" in body:
                return
        raise RuntimeError(
            f"unexpected health probe response from {url}: {resp.status_code} {resp.text[:200]}"
        )

    def query_subjects(self, base_url: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        resp = self.session.post(
            f"{base_url.rstrip('/')}/subjects/query", json=query, timeout=self.discovery_timeout
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "POST /subjects/query failed"))
        return data.get("data") or []

    def forward(
        self,
        base_url: str,
        method: str,
        path: str,
        *,
        params: Optional[List[Tuple[str, str]]] = None,
        body: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> requests.Response:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Content-Type": content_type} if content_type else {}
        logger.info(f"Forwarding {method} {url}")
        return self.session.request(
            method, url, params=params, data=body, headers=headers, timeout=self.timeout
        )
