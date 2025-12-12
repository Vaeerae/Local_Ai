from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import ExecutionContext, FixInstruction, ReviewContext, ReviewDecision


class FixManagerInput(BaseModel):
    review: ReviewContext
    execution: ExecutionContext


class FixManagerAgent(Agent[FixManagerInput, FixInstruction]):
    def __init__(self, model_name: str) -> None:
        super().__init__("FixManagerAgent", model_name)

    def run(self, data: FixManagerInput) -> FixInstruction:
        change_summary = [
            issue.detail for issue in data.review.issues
        ] or ["No issues detected, no changes."]
        retry = data.review.decision != ReviewDecision.APPROVED
        return FixInstruction(
            step_id=data.execution.step_id,
            plan_id=data.execution.plan_id,
            task_id=data.execution.task_id,
            change_summary=change_summary,
            retry=retry,
        )
