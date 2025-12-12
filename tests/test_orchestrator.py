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


def test_orchestrator_min_flow(tmp_path):
    cfg = AppConfig(
        storage_dir=tmp_path / "storage",
        context_snapshot_dir=tmp_path / "snapshots",
        runner_workspace=tmp_path / "runs",
        tool_dir=tmp_path / "tools",
    )
    orch = Orchestrator(cfg)
    orch.runner = StubRunner(cfg.runner_workspace)

    result = orch.run("Einfacher Testtask")

    assert "task" in result
    assert result["plan"]["current_step_index"] == len(result["plan"]["steps"])
    assert result["reviews"]
    assert result["summary"]["summary"]
