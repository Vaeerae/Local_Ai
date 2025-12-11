import json
from typing import Any, Dict, List

from agent_runtime import call_agent_with_repair
from config import VALIDATOR_MODEL, VALIDATOR_SYSTEM_PROMPT
from models import ValidatorResponse
from schemas import VALIDATOR_JSON_SCHEMA_HINT


def _build_validator_payload(
    user_prompt: str,
    plan: List[str],
    plan_position: int,
    step_description: str,
    executor_prompt: str,
    tools_meta: List[Dict[str, Any]],
    execution_result: Dict[str, Any],
    file_overview: List[str],
    context_log: List[str],
) -> str:
    payload = {
        "user_prompt": user_prompt,
        "plan": plan,
        "plan_position": plan_position,
        "step_description": step_description,
        "executor_prompt": executor_prompt,
        "tools": tools_meta,
        "execution": {
            "success": bool(execution_result.get("success")),
            "error": execution_result.get("error", ""),
            "traceback": execution_result.get("traceback", ""),
            "outputs": execution_result.get("outputs", []),
        },
        "file_overview": file_overview,
        "context_log": context_log,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def run_validator(
    user_prompt: str,
    plan: List[str],
    plan_position: int,
    step_description: str,
    executor_prompt: str,
    tools_meta: List[Dict[str, Any]],
    execution_result: Dict[str, Any],
    file_overview: List[str],
    context_log: List[str],
) -> Dict[str, Any]:
    user_content = _build_validator_payload(
        user_prompt,
        plan,
        plan_position,
        step_description,
        executor_prompt,
        tools_meta,
        execution_result,
        file_overview,
        context_log,
    )
    data = call_agent_with_repair(
        agent_name="Validator",
        system_prompt=str(VALIDATOR_SYSTEM_PROMPT),
        user_content=user_content,
        schema_hint=VALIDATOR_JSON_SCHEMA_HINT,
        model=VALIDATOR_MODEL,
        expected_keys=["approved", "fix_prompt"],
        model_cls=ValidatorResponse,
    )
    if isinstance(data, ValidatorResponse):
        return data.model_dump()
    return data
