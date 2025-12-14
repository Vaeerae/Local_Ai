from __future__ import annotations

from pathlib import Path

from config.config import AppConfig
from context.models import ExecutionRequest, ExecutionResult, ExecutionStatus
from orchestrator.orchestrator import Orchestrator


class StubRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.PASSED,
            stdout="stubbed",
            stderr="",
            exit_code=0,
        )


class StubLLM:
    def __init__(self):
        self.calls = []

    def generate_json(self, model: str, prompt: str):
        self.calls.append((model, prompt))
        return {}


def test_orchestrator_min_flow(tmp_path):
    cfg = AppConfig(
        storage_dir=tmp_path / "storage",
        context_snapshot_dir=tmp_path / "snapshots",
        runner_workspace=tmp_path / "runs",
        tool_dir=tmp_path / "tools",
    )
    orch = Orchestrator(cfg, llm_client=StubLLM())
    orch.runner = StubRunner(cfg.runner_workspace)

    result = orch.run("Einfacher Testtask")

    assert "task" in result
    assert result["plan"]["current_step_index"] == len(result["plan"]["steps"])
    assert result["reviews"]
    assert result["summary"]["summary"]
