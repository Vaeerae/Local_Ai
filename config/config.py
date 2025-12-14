"""
Application configuration and defaults.

The configuration is intentionally explicit and JSON-friendly so it can be
passed to agents without leaking secrets. Environment variables live in a
.env file that is never added to the agent context.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """Model selection per agent."""

    intake: str = Field(default="llama3")
    planner: str = Field(default="llama3")
    research: str = Field(default="llama3")
    decomposer: str = Field(default="llama3")
    prompter: str = Field(default="llama3")
    executor: str = Field(default="llama3")
    reviewer: str = Field(default="llama3")
    fix_manager: str = Field(default="llama3")
    summarizer: str = Field(default="llama3")


class UISettings(BaseModel):
    language: str = Field(default="de")
    streaming: bool = Field(default=True)
    workspace_path: Path = Field(default=Path.cwd())
    display_mode: str = Field(default="split")


class AppConfig(BaseSettings):
    """Central application configuration loaded from env or defaults."""

    language: str = Field(default="de")
    streaming: bool = Field(default=True)
    models: ModelConfig = Field(default_factory=ModelConfig)
    ui: UISettings = Field(default_factory=UISettings)
    storage_dir: Path = Field(default=Path("storage"))
    context_snapshot_dir: Path = Field(default=Path("context_snapshots"))
    tool_dir: Path = Field(default=Path("tools"))
    runner_workspace: Path = Field(default=Path("storage") / "runs")
    ollama_host: str = Field(default="http://localhost:11434")
    ollama_timeout: int = Field(default=60)
    allowed_tool_permissions: List[str] = Field(
        default_factory=lambda: ["python", "shell"]
    )
    project_name: str = Field(default="Local Multi-Agent Orchestrator")
    pytest_timeout_seconds: int = Field(default=120)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def as_agent_config(self) -> Dict[str, str]:
        """Expose a minimal mapping for agents to pick their model."""
        return {
            "intake": self.models.intake,
            "planner": self.models.planner,
            "research": self.models.research,
            "decomposer": self.models.decomposer,
            "prompter": self.models.prompter,
            "executor": self.models.executor,
            "reviewer": self.models.reviewer,
            "fix_manager": self.models.fix_manager,
            "summarizer": self.models.summarizer,
        }


def resolve_paths(cfg: AppConfig) -> AppConfig:
    """Ensure important directories exist and are absolute."""
    storage = cfg.storage_dir.resolve()
    snapshots = cfg.context_snapshot_dir.resolve()
    runner_workspace = cfg.runner_workspace.resolve()

    for path in (storage, snapshots, runner_workspace, cfg.tool_dir.resolve()):
        path.mkdir(parents=True, exist_ok=True)

    cfg.storage_dir = storage
    cfg.context_snapshot_dir = snapshots
    cfg.runner_workspace = runner_workspace
    return cfg
