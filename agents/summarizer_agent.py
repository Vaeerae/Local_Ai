from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import PlanContext, ProjectMemory, ReviewContext, TaskContext


class SummarizerInput(BaseModel):
    task: TaskContext
    plan: PlanContext
    reviews: list[ReviewContext]
    memory: ProjectMemory


class SummaryOutput(BaseModel):
    summary: str
    memory: ProjectMemory


class SummarizerAgent(Agent[SummarizerInput, SummaryOutput]):
    def __init__(self, model_name: str) -> None:
        super().__init__("SummarizerAgent", model_name)

    def run(self, data: SummarizerInput) -> SummaryOutput:
        issues = [r.issues for r in data.reviews]
        summary_lines = [
            f"Task: {data.task.description}",
            f"Plan steps: {[s.title for s in data.plan.steps]}",
            f"Issues: {issues}",
        ]
        memory = ProjectMemory(
            task_summaries=data.memory.task_summaries
            + [f"{data.task.task_id}: {'; '.join(summary_lines)}"],
            compressed_context="; ".join(summary_lines),
        )
        return SummaryOutput(summary="; ".join(summary_lines), memory=memory)
