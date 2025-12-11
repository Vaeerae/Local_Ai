import json
import os
from dataclasses import dataclass, asdict, field
from typing import List

from config import STATE_PATH
from io_utils import safe_open


@dataclass
class ProjectState:
    user_prompt: str = ""
    chat_summary: str = ""
    project_summary: str = ""
    project_keywords: List[str] = field(default_factory=list)
    project_infos: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    plan_position: int = 0
    context_log: List[str] = field(default_factory=list)

    @staticmethod
    def load(path: str = str(STATE_PATH)) -> "ProjectState":
        if not os.path.exists(path):
            return ProjectState()
        try:
            with safe_open(path, "r") as f:
                data = json.load(f)
        except Exception:
            print("[WARN] agent_state.json konnte nicht gelesen werden, verwende leeren State.")
            return ProjectState()

        return ProjectState(
            user_prompt=data.get("user_prompt", ""),
            chat_summary=data.get("chat_summary", ""),
            project_summary=data.get("project_summary", ""),
            project_keywords=data.get("project_keywords", []),
            project_infos=data.get("project_infos", []),
            plan=data.get("plan", []),
            plan_position=data.get("plan_position", 0),
            context_log=data.get("context_log", []),
        )

    def save(self, path: str = str(STATE_PATH)) -> None:
        with safe_open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
