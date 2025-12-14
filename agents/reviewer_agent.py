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
from prompts import build_prompt


class ReviewerInput(BaseModel):
    execution: ExecutionContext


class ReviewerAgent(Agent[ReviewerInput, ReviewContext]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("ReviewerAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

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

        recommendations: list[str] = []
        if self.llm_client:
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt(
                        "reviewer",
                        (
                            "Analysiere Testergebnisse und gib Empfehlungen als JSON.\n"
                            f"stdout:\n{execution.result.stdout}\n"
                            f"stderr:\n{execution.result.stderr}\n"
                            'Schema: { "recommendations": ["string"] }'
                        ),
                    ),
                    chunk_callback=self._stream_chunk,
                )
                recommendations = resp.get("recommendations", [])
            except Exception:
                recommendations = []

        return ReviewContext(
            step_id=execution.step_id,
            plan_id=execution.plan_id,
            task_id=execution.task_id,
            decision=decision,
            issues=issues,
            recommendations=recommendations,
            evidence={"stdout": execution.result.stdout, "stderr": execution.result.stderr},
        )
