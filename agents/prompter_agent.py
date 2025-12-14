from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import PlanContext, PromptContext, ResearchFinding, StepContext, TaskContext
from prompts import build_prompt


class PrompterInput(BaseModel):
    task: TaskContext
    step: StepContext
    plan: PlanContext
    findings: list[ResearchFinding] = []


class PrompterAgent(Agent[PrompterInput, PromptContext]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("PrompterAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

    def run(self, data: PrompterInput) -> PromptContext:
        prompt = (
            f"Step: {data.step.summary}\n"
            f"Plan: {[s.title for s in data.plan.steps]}\n"
            "Generate deterministic code and pytest to fulfill this step."
        )
        if self.llm_client:
            schema_hint = (
                '{ "prompt": "string", "tool_hints": ["python"] }\n'
                "Achte auf kurze, präzise Prompts."
            )
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt(
                        "prompter",
                        (
                            f"Erzeuge JSON mit Prompt und optional tool_hints für diesen Schritt:\n{prompt}\n"
                            f"Plan: {[s.title for s in data.plan.steps]}\n"
                            f"Funde: {[f.content for f in data.findings]}\n"
                            f"Schema: {schema_hint}"
                        ),
                        language=data.task.language,
                    ),
                    chunk_callback=self._stream_chunk,
                )
                prompt = resp.get("prompt", prompt)
                tool_hints = resp.get("tool_hints", ["python"])
            except Exception:
                tool_hints = ["python"]
        else:
            tool_hints = ["python"]
        return PromptContext(
            step_id=data.step.step_id,
            plan_id=data.step.plan_id,
            task_id=data.step.task_id,
            prompt=prompt,
            tool_hints=tool_hints,
            language=data.task.language,
        )
