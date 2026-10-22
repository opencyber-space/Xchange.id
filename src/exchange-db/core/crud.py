import os
from typing import List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection

from .schema import ExchangeSubjects, ExchangeTasks


def get_db_name() -> str:
    return f'exchange_{os.getenv("EXCHANGE_ID")}'


def get_client() -> MongoClient:
    return MongoClient(os.getenv("MONGO_URL"))


class ExchangeTasksCRUD:
    def __init__(self, client: Optional[MongoClient] = None):
        self.client = client or get_client()
        self.collection: Collection = self.client[get_db_name()]["tasks"]

    def create(self, task: ExchangeTasks) -> str:
        data = task.to_dict()
        data["_id"] = task.task_id
        self.collection.insert_one(data)
        return task.task_id

    def get(self, task_id: str) -> Optional[ExchangeTasks]:
        data = self.collection.find_one({"_id": task_id})
        if data is None:
            return None
        data.pop("_id", None)
        return ExchangeTasks.from_dict(data)

    def list(self, query: Optional[dict] = None) -> List[ExchangeTasks]:
        query = query or {}
        results = []
        for data in self.collection.find(query):
            data.pop("_id", None)
            results.append(ExchangeTasks.from_dict(data))
        return results

    def update(self, task_id: str, updates: dict) -> bool:
        result = self.collection.update_one({"_id": task_id}, {"$set": updates})
        return result.modified_count > 0

    def delete(self, task_id: str) -> bool:
        result = self.collection.delete_one({"_id": task_id})
        return result.deleted_count > 0


class ExchangeSubjectsCRUD:
    def __init__(self, client: Optional[MongoClient] = None):
        self.client = client or get_client()
        self.collection: Collection = self.client[get_db_name()]["subjects"]

    def create(self, subject: ExchangeSubjects) -> str:
        data = subject.to_dict()
        data["_id"] = subject.subject_id
        self.collection.insert_one(data)
        return subject.subject_id

    def get(self, subject_id: str) -> Optional[ExchangeSubjects]:
        data = self.collection.find_one({"_id": subject_id})
        if data is None:
            return None
        data.pop("_id", None)
        return ExchangeSubjects.from_dict(data)

    def list(self, query: Optional[dict] = None) -> List[ExchangeSubjects]:
        query = query or {}
        results = []
        for data in self.collection.find(query):
            data.pop("_id", None)
            results.append(ExchangeSubjects.from_dict(data))
        return results

    def update(self, subject_id: str, updates: dict) -> bool:
        result = self.collection.update_one({"_id": subject_id}, {"$set": updates})
        return result.modified_count > 0

    def delete(self, subject_id: str) -> bool:
        result = self.collection.delete_one({"_id": subject_id})
        return result.deleted_count > 0
