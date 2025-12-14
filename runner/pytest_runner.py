"""Run generated code using pytest in an isolated workspace."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from context.models import ExecutionRequest, ExecutionResult, ExecutionStatus


class PytestRunner:
    def __init__(self, workspace: Path, timeout_seconds: int = 120) -> None:
        self.workspace = workspace
        self.timeout_seconds = timeout_seconds
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        run_id = f"run_{uuid4()}"
        base_dir = Path(request.working_dir) if request.working_dir else self.workspace
        run_dir = base_dir
        tests_dir = run_dir / "tests"
        run_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        code_path = run_dir / "task_module.py"
        tests_path = tests_dir / "test_task_module.py"

        code_path.write_text(request.code)
        tests_path.write_text(request.tests)

        cmd = [sys.executable, "-m", "pytest", "-q", str(tests_dir)]

        result = ExecutionResult(status=ExecutionStatus.RUNNING)
        try:
            proc = subprocess.run(
                cmd,
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.status = (
                ExecutionStatus.PASSED
                if proc.returncode == 0
                else ExecutionStatus.FAILED
            )
        except subprocess.TimeoutExpired as exc:
            result.status = ExecutionStatus.FAILED
            result.stderr = f"Timed out after {self.timeout_seconds}s: {exc}"
            result.exit_code = -1
        return result
