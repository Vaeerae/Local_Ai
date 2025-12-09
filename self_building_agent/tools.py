from __future__ import annotations
import os
import subprocess
from typing import Any, Callable, Dict

ENCODING = "utf-8-sig"


def _tool_result(success: bool, message: str, output: Any = None, error: str = "") -> Dict[str, Any]:
    return {"success": success, "message": message, "output": output, "error": error}


def create_directory(path: str) -> Dict[str, Any]:
    try:
        os.makedirs(path, exist_ok=True)
        return _tool_result(True, f"Created directory {path}")
    except Exception as exc:
        return _tool_result(False, "Failed to create directory", error=str(exc))


def write_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    try:
        if os.path.exists(path) and not overwrite:
            return _tool_result(False, "File exists and overwrite is False")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding=ENCODING) as f:
            f.write(content)
        return _tool_result(True, f"Wrote file {path}", output=len(content))
    except Exception as exc:
        return _tool_result(False, "Failed to write file", error=str(exc))


def run_shell(command: str, workdir: str = ".") -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
        success = proc.returncode == 0
        return _tool_result(
            success,
            "Command executed" if success else f"Command failed ({proc.returncode})",
            output=proc.stdout.strip(),
            error=proc.stderr.strip(),
        )
    except Exception as exc:
        return _tool_result(False, "Exception during command", error=str(exc))


def append_tool_from_template(name: str, template_lines: Any) -> Dict[str, Any]:
    """Append a new tool function to this file using provided template lines."""
    try:
        if not template_lines:
            return _tool_result(False, "No template provided")
        if isinstance(template_lines, list):
            code = "\n".join(template_lines)
        else:
            code = str(template_lines)
        with open(__file__, "r", encoding=ENCODING) as f:
            content = f.read()
        if f"def {name}" in content:
            return _tool_result(True, f"Tool {name} already exists; skipped append")
        with open(__file__, "a", encoding=ENCODING) as f:
            f.write("\n\n" + code + "\n")
        return _tool_result(True, f"Appended tool {name}")
    except Exception as exc:
        return _tool_result(False, "Failed to append tool", error=str(exc))


def load_tools() -> Dict[str, Callable]:
    """Return callable tools dictionary."""
    candidates = {
        "create_directory": create_directory,
        "write_file": write_file,
        "run_shell": run_shell,
    }
    # Include any additional callables defined after import
    for name, func in list(globals().items()):
        if name.startswith("_"):
            continue
        if callable(func) and name not in candidates:
            candidates[name] = func
    return candidates


__all__ = ["create_directory", "write_file", "run_shell", "append_tool_from_template", "load_tools"]
