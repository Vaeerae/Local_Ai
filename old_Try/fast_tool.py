"""
Helper to execute fast tools requested by the Executor (e.g., quick file reads).
"""
from typing import Any, Dict


def run_fast_tool(tool_name: str, args: Dict[str, Any], tool_funcs: Dict[str, Any]) -> Dict[str, Any]:
    func = tool_funcs.get(tool_name)
    if func is None:
        return {
            "success": False,
            "error": f"Fast-Tool '{tool_name}' nicht gefunden.",
            "traceback": "",
            "outputs": [],
        }
    try:
        result = func(**(args or {}))
        return {
            "success": True,
            "error": "",
            "traceback": "",
            "outputs": [{"tool_name": tool_name, "result": result}],
        }
    except Exception as exc:  # pragma: no cover - defensive
        import traceback

        return {
            "success": False,
            "error": f"Fast-Tool '{tool_name}' Exception: {exc}",
            "traceback": traceback.format_exc(),
            "outputs": [],
        }
