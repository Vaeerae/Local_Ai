import json
from typing import Any, Dict, List

from agent_runtime import call_agent_with_repair
from config import EXECUTOR_MODEL, EXECUTOR_SYSTEM_PROMPT
from models import ExecutorResponse
from schemas import EXECUTOR_JSON_SCHEMA_HINT


def _build_executor_payload(
    user_prompt: str,
    plan: List[str],
    plan_position: int,
    current_step: str,
    executor_prompt: str,
    tools_meta: List[Dict[str, Any]],
    file_overview: List[str],
    context_log: List[str],
) -> str:
    payload = {
        "user_prompt": user_prompt,
        "plan": plan,
        "plan_position": plan_position,
        "current_step": current_step,
        "executor_prompt": executor_prompt,
        "known_tools": tools_meta,
        "file_overview": file_overview,
        "context_log": context_log,
        "hint": (
            "Du fuehrst keinen Code aus. Definiere Tools oder nutze bestehende Tools. "
            "Wenn du schnelle Infos brauchst (z.B. Dateien lesen), setze fast_infos=true "
            "und nenne fast_tool + fast_args."
        ),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def run_executor(
    user_prompt: str,
    plan: List[str],
    plan_position: int,
    current_step: str,
    executor_prompt: str,
    tools_meta: List[Dict[str, Any]],
    file_overview: List[str],
    context_log: List[str],
) -> Dict[str, Any]:
    user_content = _build_executor_payload(
        user_prompt,
        plan,
        plan_position,
        current_step,
        executor_prompt,
        tools_meta,
        file_overview,
        context_log,
    )
    data = call_agent_with_repair(
        agent_name="Executor",
        system_prompt=str(EXECUTOR_SYSTEM_PROMPT),
        user_content=user_content,
        schema_hint=EXECUTOR_JSON_SCHEMA_HINT,
        model=EXECUTOR_MODEL,
        expected_keys=["actions", "new_tools", "picked_prompt", "fast_infos"],
        model_cls=ExecutorResponse,
    )
    if isinstance(data, ExecutorResponse):
        return data.model_dump()
    return data
