from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import PlanContext, ProjectMemory, ReviewContext, TaskContext
from prompts import build_prompt


class SummarizerInput(BaseModel):
    task: TaskContext
    plan: PlanContext
    reviews: list[ReviewContext]
    memory: ProjectMemory


class SummaryOutput(BaseModel):
    summary: str
    memory: ProjectMemory


class SummarizerAgent(Agent[SummarizerInput, SummaryOutput]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("SummarizerAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

    def run(self, data: SummarizerInput) -> SummaryOutput:
        issues = [r.issues for r in data.reviews]
        summary_lines = [
            f"Task: {data.task.description}",
            f"Plan steps: {[s.title for s in data.plan.steps]}",
            f"Issues: {issues}",
        ]
        if self.llm_client:
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt(
                        "summarizer",
                        (
                            "Fasse den Run als JSON zusammen. Schema: "
                            '{ "summary": "string" }.\n'
                            f"Task: {data.task.description}\n"
                            f"Plan: {[s.title for s in data.plan.steps]}\n"
                            f"Issues: {issues}\n"
                        ),
                    ),
                    chunk_callback=self._stream_chunk,
                )
                summary_text = resp.get("summary", "; ".join(summary_lines))
            except Exception:
                summary_text = "; ".join(summary_lines)
        else:
            summary_text = "; ".join(summary_lines)

        memory = ProjectMemory(
            task_summaries=data.memory.task_summaries
            + [f"{data.task.task_id}: {summary_text}"],
            compressed_context=summary_text,
        )
        return SummaryOutput(summary=summary_text, memory=memory)
