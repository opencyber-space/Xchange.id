from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

STATUS_UNKNOWN = "unknown"
STATUS_HEALTHY = "healthy"
STATUS_UNREACHABLE = "unreachable"


def _to_iso(value: Optional[datetime]):
    return value.isoformat() if isinstance(value, datetime) else value


def _from_iso(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


@dataclass
class ExchangeEntry:
    exchange_id: str
    exchange_api_url: str
    exchange_name: str = ""
    exchange_description: str = ""
    exchange_tags: List[str] = field(default_factory=list)
    exchange_metadata: dict = field(default_factory=dict)
    exchange_status: str = STATUS_UNKNOWN
    registration_time: Optional[datetime] = None
    last_health_check_time: Optional[datetime] = None
    last_health_check_error: str = ""

    def to_dict(self) -> dict:
        return {
            "exchange_id": self.exchange_id,
            "exchange_api_url": self.exchange_api_url,
            "exchange_name": self.exchange_name,
            "exchange_description": self.exchange_description,
            "exchange_tags": self.exchange_tags,
            "exchange_metadata": self.exchange_metadata,
            "exchange_status": self.exchange_status,
            "registration_time": _to_iso(self.registration_time),
            "last_health_check_time": _to_iso(self.last_health_check_time),
            "last_health_check_error": self.last_health_check_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExchangeEntry":
        return cls(
            exchange_id=data["exchange_id"],
            exchange_api_url=data["exchange_api_url"],
            exchange_name=data.get("exchange_name", ""),
            exchange_description=data.get("exchange_description", ""),
            exchange_tags=list(data.get("exchange_tags", [])),
            exchange_metadata=data.get("exchange_metadata", {}),
            exchange_status=data.get("exchange_status", STATUS_UNKNOWN),
            registration_time=_from_iso(data.get("registration_time")),
            last_health_check_time=_from_iso(data.get("last_health_check_time")),
            last_health_check_error=data.get("last_health_check_error", ""),
        )
