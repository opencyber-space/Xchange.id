import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .crud import ExchangeRegistryCRUD
from .exchange_client import ExchangeClient
from .schema import ExchangeEntry

logger = logging.getLogger(__name__)


def build_registry_query(
    query: Optional[dict] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
) -> dict:
    filters = []
    if query:
        filters.append(query)
    if tags:
        filters.append({"exchange_tags": {"$in": tags}})
    if status:
        filters.append({"exchange_status": status})

    if not filters:
        return {}
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def build_subject_query(
    subject_query: Optional[dict] = None,
    subject_topics: Optional[List[str]] = None,
) -> Optional[dict]:
    filters = []
    if subject_query:
        filters.append(subject_query)
    if subject_topics:
        filters.append({"topics": {"$in": subject_topics}})

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


class DiscoveryService:
    def __init__(
        self,
        *,
        registry_crud: ExchangeRegistryCRUD,
        exchange_client: ExchangeClient,
        num_workers: int = 8,
    ):
        self._registry_crud = registry_crud
        self._exchange_client = exchange_client
        self._pool = ThreadPoolExecutor(max_workers=max(1, num_workers))

    def discover(
        self,
        *,
        registry_query: dict,
        subject_query: Optional[dict] = None,
    ) -> Dict[str, Any]:
        candidates = self._registry_crud.list(registry_query)

        if subject_query is None:
            return {"exchanges": [e.to_dict() for e in candidates], "unreachable": []}

        outcomes = list(
            self._pool.map(lambda e: self._match_subjects(e, subject_query), candidates)
        )

        matches = []
        unreachable = []
        for entry, subject_ids, error in outcomes:
            if error is not None:
                unreachable.append({"exchange_id": entry.exchange_id, "error": error})
            elif subject_ids:
                matches.append({**entry.to_dict(), "matching_subject_ids": subject_ids})

        matches.sort(key=lambda m: len(m["matching_subject_ids"]), reverse=True)
        return {"exchanges": matches, "unreachable": unreachable}

    def _match_subjects(self, entry: ExchangeEntry, subject_query: dict):
        try:
            subjects = self._exchange_client.query_subjects(entry.exchange_api_url, subject_query)
            return entry, [s["subject_id"] for s in subjects], None
        except Exception as e:
            logger.warning(f"Subject query failed for exchange '{entry.exchange_id}': {e}")
            return entry, None, str(e)
