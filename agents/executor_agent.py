from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel

from agents.base import Agent
from context.models import ExecutionRequest, PromptContext, ResearchFinding, StepContext
from prompts import build_prompt


class ExecutorInput(BaseModel):
    step: StepContext
    prompt: PromptContext
    findings: list[ResearchFinding] = []


class ExecutorAgent(Agent[ExecutorInput, ExecutionRequest]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("ExecutorAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

    def run(self, data: ExecutorInput) -> ExecutionRequest:
        """
        Generate code/tests via LLM if available; fallback is deterministic placeholder.
        The code should address the prompt, e.g., writing files or running tasks.
        """
        code = (
            "def run_task(path: str = 'output.txt', content: str = 'ok'):\n"
            '    """Write content to a file and return path."""\n'
            "    with open(path, 'w', encoding='utf-8') as f:\n"
            "        f.write(content)\n"
            "    return path\n"
        )
        tests = (
            "from task_module import run_task\n\n"
            "def test_run_task(tmp_path):\n"
            "    target = tmp_path / 'output.txt'\n"
            "    p = run_task(str(target), 'ok')\n"
            "    assert target.read_text(encoding='utf-8') == 'ok'\n"
            "    assert p.endswith('output.txt')\n"
        )
        expected_output = "output.txt"

        if self.llm_client:
            schema_hint = (
                '{ "code": "python code", "tests": "pytest code", "expected_output": "string" }'
            )
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt(
                        "executor",
                        (
                            "Erzeuge Python-Code und pytest-Tests als JSON für diesen Schritt.\n"
                            f"Aufgabe:\n{data.prompt.prompt}\n"
                            f"Funde: {[f.content for f in data.findings]}\n"
                            f"Schema: {schema_hint}\n"
                            "Nur kompakten, deterministischen Code, keine Kommentare."
                        ),
                        language=data.prompt.language,
                    ),
                    chunk_callback=self._stream_chunk,
                )
                code = resp.get("code", code)
                tests = resp.get("tests", tests)
                expected_output = resp.get("expected_output", expected_output)
            except Exception:
                pass
        return ExecutionRequest(
            code=code,
            tests=tests,
            expected_output=expected_output,
            working_dir=Path.cwd(),
        )
