import os
from typing import Any, Dict, List, Optional, Tuple

import requests


class BiddingClient:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: Tuple[int, int] = (10, 30),
    ):
        self.base_url = (base_url or os.environ["BIDDING_SERVICE_URL"]).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def create_bid_job(self, **kwargs: Any) -> Dict[str, Any]:
        return self._request("post", "/bid-jobs", json=kwargs)

    def get_bid_job(self, bid_job_id: str) -> Dict[str, Any]:
        return self._request("get", f"/bid-jobs/{bid_job_id}")

    def get_bids(self, bid_job_id: str) -> List[Dict[str, Any]]:
        return self._request("get", f"/bid-jobs/{bid_job_id}/bids")

    def get_task_results(self, bid_job_id: str) -> List[Dict[str, Any]]:
        return self._request("get", f"/bid-jobs/{bid_job_id}/task-results")

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self.session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error", f"{method.upper()} {path} failed"))
        return data.get("data")
