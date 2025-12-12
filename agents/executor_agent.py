from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import ExecutionRequest, PromptContext, StepContext


class ExecutorInput(BaseModel):
    step: StepContext
    prompt: PromptContext


class ExecutorAgent(Agent[ExecutorInput, ExecutionRequest]):
    def __init__(self, model_name: str) -> None:
        super().__init__("ExecutorAgent", model_name)

    def run(self, data: ExecutorInput) -> ExecutionRequest:
        """
        Generate deterministic placeholder code and tests. This keeps the flow runnable
        without relying on an LLM while respecting the required contracts.
        """
        code = (
            "def run_task():\n"
            '    """Deterministic placeholder implementation."""\n'
            "    return 'ok'\n"
        )
        tests = (
            "from task_module import run_task\n\n"
            "def test_run_task():\n"
            "    assert run_task() == 'ok'\n"
        )
        return ExecutionRequest(
            code=code,
            tests=tests,
            expected_output="ok",
        )
