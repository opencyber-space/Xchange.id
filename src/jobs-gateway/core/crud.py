import os
from typing import List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection

from .schema import ExchangeEntry


def get_db_name() -> str:
    return os.getenv("GATEWAY_DB_NAME", "xchange_gateway")


def get_client() -> MongoClient:
    return MongoClient(os.getenv("MONGO_URL"))


class ExchangeRegistryCRUD:
    def __init__(self, client: Optional[MongoClient] = None):
        self.client = client or get_client()
        self.collection: Collection = self.client[get_db_name()]["exchanges"]

    def create(self, entry: ExchangeEntry) -> str:
        data = entry.to_dict()
        data["_id"] = entry.exchange_id
        self.collection.insert_one(data)
        return entry.exchange_id

    def get(self, exchange_id: str) -> Optional[ExchangeEntry]:
        data = self.collection.find_one({"_id": exchange_id})
        if data is None:
            return None
        data.pop("_id", None)
        return ExchangeEntry.from_dict(data)

    def list(self, query: Optional[dict] = None) -> List[ExchangeEntry]:
        query = query or {}
        results = []
        for data in self.collection.find(query):
            data.pop("_id", None)
            results.append(ExchangeEntry.from_dict(data))
        return results

    def update(self, exchange_id: str, updates: dict) -> bool:
        result = self.collection.update_one({"_id": exchange_id}, {"$set": updates})
        return result.modified_count > 0

    def delete(self, exchange_id: str) -> bool:
        result = self.collection.delete_one({"_id": exchange_id})
        return result.deleted_count > 0
