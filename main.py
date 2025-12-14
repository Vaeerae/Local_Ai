from __future__ import annotations

import argparse
import json
import sys

from config.config import AppConfig
from orchestrator.orchestrator import Orchestrator
from ui.app import run_ui


def main() -> int:
    parser = argparse.ArgumentParser(description="Local multi-agent orchestrator")
    parser.add_argument("task", nargs="*", help="Task description")
    args = parser.parse_args()

    task_description = " ".join(args.task) if args.task else "Implement placeholder task"
    app_cfg = AppConfig()
    orchestrator = Orchestrator(app_cfg)
    plan_steps = []
    status = "Bereit"
    if args.task:
        result = orchestrator.run(task_description)
        print(json.dumps(result, indent=2, ensure_ascii=True, default=str))
        status = f"{len(result.get('plan', {}).get('steps', []))} steps processed"
        plan_steps = [s.get("title") for s in result.get("plan", {}).get("steps", [])]
    try:
        run_ui(
            orchestrator.config.project_name,
            status_text=status,
            workspace_path=orchestrator.config.ui.workspace_path,
            task_description=task_description,
            plan_steps=plan_steps,
            language=orchestrator.config.language,
            models=orchestrator.config.models.model_dump(),
            orchestrator=orchestrator,
        )
    except RuntimeError as exc:
        print(f"UI konnte nicht gestartet werden: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
