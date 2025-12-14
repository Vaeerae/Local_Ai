from __future__ import annotations

from pathlib import Path
import os
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
            "from pathlib import Path\n"
            "import os\n"
            "\n"
            "def run_task(filename: str = 'output.txt', content: str = 'ok'):\n"
            '    \"\"\"Write content to USER_DATA_DIR/filename and return path.\"\"\"\n'
            "    data_dir = Path(os.environ.get('USER_DATA_DIR', '.'))\n"
            "    data_dir.mkdir(parents=True, exist_ok=True)\n"
            "    target = data_dir / filename\n"
            "    target.write_text(content, encoding='utf-8')\n"
            "    return str(target)\n"
        )
        tests = (
            "from task_module import run_task\n"
            "from pathlib import Path\n"
            "import os\n\n"
            "def test_run_task():\n"
            "    p = Path(run_task('output.txt', 'ok'))\n"
            "    assert p.read_text(encoding='utf-8') == 'ok'\n"
            "    assert p.name == 'output.txt'\n"
        )
        expected_output = "output.txt"

        if self.llm_client:
            schema_hint = (
                '{ "code": "python code", "tests": "pytest code", "expected_output": "string" }'
            )
            extra = [
                ("Aktueller Planschritt", data.step.summary),
                ("Prompt vom Prompter", data.prompt.prompt),
                ("Funde Research", "; ".join(f.content for f in data.findings)),
            ]
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
                        history=[
                            ("Planner", "siehe Plan oben"),
                            ("Decomposer", data.step.summary),
                            ("Research", "; ".join(f.content for f in data.findings)),
                            ("Prompter", data.prompt.prompt),
                        ],
                        infos=[f"{k}: {v}" for k, v in [("Schema", schema_hint)] + [(a, b) for a, b in extra]],
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
