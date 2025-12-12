from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import (
    ExecutionContext,
    ExecutionStatus,
    Issue,
    ReviewContext,
    ReviewDecision,
)


class ReviewerInput(BaseModel):
    execution: ExecutionContext


class ReviewerAgent(Agent[ReviewerInput, ReviewContext]):
    def __init__(self, model_name: str) -> None:
        super().__init__("ReviewerAgent", model_name)

    def run(self, data: ReviewerInput) -> ReviewContext:
        execution = data.execution
        issues: list[Issue] = []
        decision = ReviewDecision.APPROVED

        if execution.result.status != ExecutionStatus.PASSED:
            decision = ReviewDecision.CHANGES_REQUIRED
            issues.append(
                Issue(
                    title="Tests failed",
                    detail=execution.result.stderr or execution.result.stdout,
                    severity="critical",
                )
            )

        return ReviewContext(
            step_id=execution.step_id,
            plan_id=execution.plan_id,
            task_id=execution.task_id,
            decision=decision,
            issues=issues,
            recommendations=[],
            evidence={"stdout": execution.result.stdout, "stderr": execution.result.stderr},
        )
