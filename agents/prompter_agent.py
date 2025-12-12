from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import PlanContext, PromptContext, StepContext


class PrompterInput(BaseModel):
    step: StepContext
    plan: PlanContext


class PrompterAgent(Agent[PrompterInput, PromptContext]):
    def __init__(self, model_name: str) -> None:
        super().__init__("PrompterAgent", model_name)

    def run(self, data: PrompterInput) -> PromptContext:
        prompt = (
            f"Step: {data.step.summary}\n"
            f"Plan: {[s.title for s in data.plan.steps]}\n"
            "Generate deterministic code and pytest to fulfill this step."
        )
        return PromptContext(
            step_id=data.step.step_id,
            plan_id=data.step.plan_id,
            task_id=data.step.task_id,
            prompt=prompt,
            tool_hints=["python"],
        )
