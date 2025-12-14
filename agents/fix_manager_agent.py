from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import ExecutionContext, FixInstruction, ReviewContext, ReviewDecision
from prompts import build_prompt


class FixManagerInput(BaseModel):
    review: ReviewContext
    execution: ExecutionContext


class FixManagerAgent(Agent[FixManagerInput, FixInstruction]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("FixManagerAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

    def run(self, data: FixManagerInput) -> FixInstruction:
        change_summary = [
            issue.detail for issue in data.review.issues
        ] or ["No issues detected, no changes."]
        retry = data.review.decision != ReviewDecision.APPROVED

        if self.llm_client and retry:
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt(
                        "fix_manager",
                        (
                            "Schlage konkrete Fix-Schritte als JSON vor.\n"
                            f"Issues: {[i.detail for i in data.review.issues]}\n"
                            'Schema: { "change_summary": ["string"], "retry": true }'
                        ),
                        language=data.execution.prompt.language,
                    ),
                    chunk_callback=self._stream_chunk,
                )
                change_summary = resp.get("change_summary", change_summary)
                retry = resp.get("retry", retry)
            except Exception:
                pass
        return FixInstruction(
            step_id=data.execution.step_id,
            plan_id=data.execution.plan_id,
            task_id=data.execution.task_id,
            change_summary=change_summary,
            retry=retry,
        )
