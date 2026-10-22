import os
import logging
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class SubjectTask:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: Tuple[int, int] = (10, 300),
    ):
        self.base_url = (base_url or os.environ["SUBJECT_DELEGATE_URL"]).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def submit_and_wait(
        self,
        *,
        subject_id: str,
        session_id: str,
        task_id: str,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/submit-and-wait"
        payload = {
            "subject_id": subject_id,
            "session_id": session_id,
            "task_id": task_id,
            "task_data": task_data,
        }

        logger.info(f"Submitting task '{task_id}' for subject '{subject_id}' to {url}")
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
