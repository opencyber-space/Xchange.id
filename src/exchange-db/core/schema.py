from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class ExchangeTasks:
    task_id: str
    task_assignment_type: str
    task_data: Any
    task_assignment_status: str
    task_metadata: dict = field(default_factory=dict)
    taski_creation_time: Optional[datetime] = None
    task_output: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_assignment_type": self.task_assignment_type,
            "task_data": self.task_data,
            "task_assignment_status": self.task_assignment_status,
            "task_metadata": self.task_metadata,
            "taski_creation_time": self.taski_creation_time.isoformat()
            if isinstance(self.taski_creation_time, datetime)
            else self.taski_creation_time,
            "task_output": self.task_output,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExchangeTasks":
        creation_time = data.get("taski_creation_time")
        if isinstance(creation_time, str):
            creation_time = datetime.fromisoformat(creation_time)

        return cls(
            task_id=data["task_id"],
            task_assignment_type=data["task_assignment_type"],
            task_data=data.get("task_data"),
            task_assignment_status=data["task_assignment_status"],
            task_metadata=data.get("task_metadata", {}),
            taski_creation_time=creation_time,
            task_output=data.get("task_output", {}),
        )


@dataclass
class ExchangeSubjects:
    subject_id: str
    subject_metadata: dict = field(default_factory=dict)
    task_evaluation_function: str = ""
    subject_capabilities: dict = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "subject_metadata": self.subject_metadata,
            "task_evaluation_function": self.task_evaluation_function,
            "subject_capabilities": self.subject_capabilities,
            "topics": self.topics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExchangeSubjects":
        return cls(
            subject_id=data["subject_id"],
            subject_metadata=data.get("subject_metadata", {}),
            task_evaluation_function=data.get("task_evaluation_function", ""),
            subject_capabilities=data.get("subject_capabilities", {}),
            topics=list(data.get("topics", [])),
        )
