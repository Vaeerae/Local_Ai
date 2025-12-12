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
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Start the PySide6 UI after the run",
    )
    args = parser.parse_args()

    task_description = " ".join(args.task) if args.task else "Implement placeholder task"
    orchestrator = Orchestrator(AppConfig())
    result = orchestrator.run(task_description)
    print(json.dumps(result, indent=2, ensure_ascii=True, default=str))

    if args.ui:
        status = f"{len(result.get('plan', {}).get('steps', []))} steps processed"
        try:
            run_ui(orchestrator.config.project_name, status_text=status)
        except RuntimeError as exc:
            print(f"UI konnte nicht gestartet werden: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
