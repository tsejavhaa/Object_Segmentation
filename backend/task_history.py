import uuid
import time
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TaskRecord:
    def __init__(
        self,
        task_id: str,
        model_name: str,
        file_name: str,
        mask_count: int,
        computation_time: float,
        status: str,
        error_message: Optional[str] = None,
        overlay_url: Optional[str] = None,
        mask_url: Optional[str] = None,
        original_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.task_id = task_id
        self.timestamp = datetime.now().isoformat()
        self.model_name = model_name
        self.file_name = file_name
        self.mask_count = mask_count
        self.computation_time = computation_time
        self.status = status
        self.error_message = error_message
        self.overlay_url = overlay_url
        self.mask_url = mask_url
        self.original_url = original_url
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "model_name": self.model_name,
            "file_name": self.file_name,
            "mask_count": self.mask_count,
            "computation_time": self.computation_time,
            "status": self.status,
            "error_message": self.error_message,
            "overlay_url": self.overlay_url,
            "mask_url": self.mask_url,
            "original_url": self.original_url,
            "metadata": self.metadata,
        }


class TaskHistoryStore:
    def __init__(self, max_tasks: int = 100):
        self._tasks: list[TaskRecord] = []
        self._max_tasks = max_tasks

    def add(self, record: TaskRecord) -> None:
        self._tasks.insert(0, record)
        if len(self._tasks) > self._max_tasks:
            self._tasks.pop()

    def get_all(self) -> list[dict]:
        return [t.to_dict() for t in self._tasks]

    def get(self, task_id: str) -> Optional[dict]:
        for t in self._tasks:
            if t.task_id == task_id:
                return t.to_dict()
        return None


_history_store = TaskHistoryStore()


def get_history_store() -> TaskHistoryStore:
    return _history_store