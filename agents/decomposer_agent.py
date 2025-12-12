from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base import Agent
from context.models import PlanContext, StepContext, StepStatus


class DecomposerInput(BaseModel):
    plan: PlanContext
    step_index: int = Field(ge=0)


class DecomposerAgent(Agent[DecomposerInput, StepContext]):
    def __init__(self, model_name: str) -> None:
        super().__init__("DecomposerAgent", model_name)

    def run(self, data: DecomposerInput) -> StepContext:
        if data.step_index >= len(data.plan.steps):
            raise IndexError("Step index out of range.")

        step = data.plan.steps[data.step_index]
        return StepContext(
            step_id=step.step_id,
            plan_id=data.plan.plan_id,
            task_id=data.plan.task_id,
            summary=step.summary,
            status=StepStatus.PENDING,
            attempt=1,
        )
