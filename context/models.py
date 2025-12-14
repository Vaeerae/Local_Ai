"""
Pydantic context models that are passed between agents.

Each context is minimal and JSON-serializable to enforce deterministic orchestration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from tools.manifest import ToolManifest


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"


class BaseContext(BaseModel):
    context_version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": "forbid"}


class TaskContext(BaseContext):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    language: str = Field(default="de")


class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    summary: str
    status: StepStatus = Field(default=StepStatus.PENDING)
    dependencies: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class PlanContext(BaseContext):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    steps: List[PlanStep]
    current_step_index: int = Field(default=0)
    version: str = Field(default="0.1.0")


class StepContext(BaseContext):
    step_id: str
    plan_id: str
    task_id: str
    summary: str
    attempt: int = Field(default=1)
    status: StepStatus = Field(default=StepStatus.PENDING)


class PromptContext(BaseContext):
    step_id: str
    plan_id: str
    task_id: str
    prompt: str
    tool_hints: List[str] = Field(default_factory=list)
    language: str = "de"


class ExecutionRequest(BaseModel):
    code: str
    tests: str
    expected_output: Optional[str] = None
    working_dir: Path = Field(default_factory=Path.cwd)

    model_config = {"extra": "forbid"}


class ExecutionResult(BaseModel):
    status: ExecutionStatus = Field(default=ExecutionStatus.NOT_RUN)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    traceback: Optional[str] = None
    exit_code: Optional[int] = None
    test_report: Dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class ToolResult(BaseModel):
    name: str
    stdout: str = ""
    stderr: str = ""
    artifacts: List[Path] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class ResearchFinding(BaseModel):
    source: str
    content: str

    model_config = {"extra": "forbid"}


class ExecutionContext(BaseContext):
    step_id: str
    plan_id: str
    task_id: str
    prompt: PromptContext
    request: ExecutionRequest
    result: ExecutionResult = Field(default_factory=ExecutionResult)
    tool_outputs: List[ToolResult] = Field(default_factory=list)
    research_findings: List[ResearchFinding] = Field(default_factory=list)


class Issue(BaseModel):
    title: str
    detail: str
    severity: str = Field(default="major")  # critical/major/minor

    model_config = {"extra": "forbid"}


class ReviewContext(BaseContext):
    step_id: str
    plan_id: str
    task_id: str
    decision: ReviewDecision
    issues: List[Issue] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    evidence: Dict[str, str] = Field(default_factory=dict)


class FixInstruction(BaseModel):
    step_id: str
    plan_id: str
    task_id: str
    change_summary: List[str] = Field(default_factory=list)
    retry: bool = Field(default=False)

    model_config = {"extra": "forbid"}


class ProjectMemory(BaseContext):
    task_summaries: List[str] = Field(default_factory=list)
    compressed_context: str = Field(default="")


class ToolRef(BaseModel):
    name: str
    version: str
    permissions: List[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class ToolRegistryContext(BaseContext):
    tools: List[ToolRef] = Field(default_factory=list)
    manifests: Dict[str, ToolManifest] = Field(default_factory=dict)


class UIState(BaseContext):
    language: str = Field(default="de")
    streaming: bool = Field(default=True)
    selected_agent_models: Dict[str, str] = Field(default_factory=dict)
    workspace_path: Path = Field(default_factory=Path.cwd)
    display_mode: str = Field(default="split")
