import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from config import TOOLS_META_PATH, TOOLS_PY_PATH
from io_utils import safe_open


def ensure_tools_files_exist() -> None:
    """Create tools.py and tools.json if missing."""
    if not Path(TOOLS_PY_PATH).exists():
        with safe_open(TOOLS_PY_PATH, "w") as f:
            f.write("# Automatisch generiertes Tools-Modul\n\nTOOL_REGISTRY = {}\n")

    if not Path(TOOLS_META_PATH).exists():
        with safe_open(TOOLS_META_PATH, "w") as f:
            json.dump([], f, indent=2, ensure_ascii=False)


def load_tools_meta() -> List[Dict[str, Any]]:
    ensure_tools_files_exist()
    with safe_open(TOOLS_META_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
    if not isinstance(data, list):
        data = []
    return data


def save_tools_meta(meta: List[Dict[str, Any]]) -> None:
    with safe_open(TOOLS_META_PATH, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def load_tool_functions() -> Dict[str, Any]:
    ensure_tools_files_exist()
    try:
        if "tools" in sys.modules:
            importlib.reload(sys.modules["tools"])
            mod = sys.modules["tools"]
        else:
            mod = importlib.import_module("tools")
        registry = getattr(mod, "TOOL_REGISTRY", {})
        if not isinstance(registry, dict):
            return {}
        return registry
    except Exception as exc:
        print(f"[WARN] Konnte tools-Modul nicht laden: {exc}", file=sys.stderr)
        return {}


def append_new_tools(new_tools: List[Dict[str, Any]]) -> None:
    """
    Persistiert vom Executor vorgeschlagene Tools in tools.json und tools.py.
    """
    if not new_tools:
        return

    ensure_tools_files_exist()

    meta = load_tools_meta()
    existing_names = {t.get("nameTool") for t in meta}

    with safe_open(TOOLS_PY_PATH, "a") as f_py:
        for tool in new_tools:
            name = tool.get("nameTool")
            code = tool.get("python_code", "")
            if not name or not code:
                continue

            if name not in existing_names:
                meta_entry = {
                    "nameTool": name,
                    "beschreib": tool.get("beschreib", ""),
                    "args": tool.get("args", ""),
                    "ergebniss": tool.get("ergebniss", ""),
                }
                meta.append(meta_entry)
                existing_names.add(name)

            f_py.write("\n\n")
            f_py.write(code.strip())
            f_py.write("\n")
            f_py.write(f'TOOL_REGISTRY["{name}"] = {name}\n')

    save_tools_meta(meta)
