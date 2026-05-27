from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SegmentRequest(BaseModel):
    file_path: str
    model_name: str = "sam3"


class SegmentResponse(BaseModel):
    overlay_url: str
    mask_url: str
    num_masks: int
    original_url: str
    model_name: str
    computation_time: float


class ModelInfo(BaseModel):
    name: str
    display_name: str
    description: str
    loaded: bool


class ModelsList(BaseModel):
    models: list[ModelInfo]


class StatusResponse(BaseModel):
    status: str
    model_loaded: bool
    active_model: Optional[str] = None


class TaskRecord(BaseModel):
    task_id: str
    timestamp: str
    model_name: str
    file_name: str
    mask_count: int
    computation_time: float
    status: str
    error_message: Optional[str] = None
    overlay_url: Optional[str] = None
    mask_url: Optional[str] = None
    original_url: Optional[str] = None
    metadata: Optional[dict] = None


class TaskHistory(BaseModel):
    tasks: list[TaskRecord]