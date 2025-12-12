from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import TaskContext


class IntakeInput(BaseModel):
    description: str
    language: str = "de"


class IntakeAgent(Agent[IntakeInput, TaskContext]):
    def __init__(self, model_name: str) -> None:
        super().__init__("IntakeAgent", model_name)

    def run(self, data: IntakeInput) -> TaskContext:
        return TaskContext(description=data.description, language=data.language)
