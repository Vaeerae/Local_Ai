"""Event definitions and persistence models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    PLAN_CREATED = "PLAN_CREATED"
    STEP_EXECUTED = "STEP_EXECUTED"
    TEST_FAILED = "TEST_FAILED"
    TOOL_REGISTERED = "TOOL_REGISTERED"
    ERROR_ABORTED = "ERROR_ABORTED"
    RUN_COMPLETED = "RUN_COMPLETED"


class EventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]

    model_config = {"extra": "forbid"}
