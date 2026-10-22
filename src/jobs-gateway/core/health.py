import logging
import threading
import time
from datetime import datetime

from .crud import ExchangeRegistryCRUD
from .exchange_client import ExchangeClient
from .schema import STATUS_HEALTHY, STATUS_UNREACHABLE, ExchangeEntry

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(
        self,
        *,
        registry_crud: ExchangeRegistryCRUD,
        exchange_client: ExchangeClient,
        interval: float = 30.0,
    ):
        self._registry_crud = registry_crud
        self._exchange_client = exchange_client
        self._interval = interval
        self._thread = None

    def check(self, entry: ExchangeEntry) -> ExchangeEntry:
        try:
            self._exchange_client.check_health(entry.exchange_api_url)
            entry.exchange_status = STATUS_HEALTHY
            entry.last_health_check_error = ""
        except Exception as e:
            logger.warning(f"Health check failed for exchange '{entry.exchange_id}': {e}")
            entry.exchange_status = STATUS_UNREACHABLE
            entry.last_health_check_error = str(e)

        entry.last_health_check_time = datetime.utcnow()
        self._registry_crud.update(
            entry.exchange_id,
            {
                "exchange_status": entry.exchange_status,
                "last_health_check_time": entry.last_health_check_time.isoformat(),
                "last_health_check_error": entry.last_health_check_error,
            },
        )
        return entry

    def check_all(self) -> None:
        for entry in self._registry_crud.list():
            self.check(entry)

    def start(self) -> None:
        if self._interval <= 0 or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                self.check_all()
            except Exception as e:
                logger.error(f"Health check sweep failed: {e}")
            time.sleep(self._interval)
