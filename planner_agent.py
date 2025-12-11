import json
from typing import Any, Dict, Optional

from agent_runtime import call_agent_with_repair
from config import DEFAULT_MODEL, PLANNER_SYSTEM_PROMPT
from models import PlannerResponse
from schemas import PLANNER_JSON_SCHEMA_HINT
from state import ProjectState


def _build_planner_context(user_input: str, state: ProjectState, step_index: Optional[int]) -> str:
    context = {
        "user_prompt": user_input,
        "chat_summary": state.chat_summary,
        "project_summary": state.project_summary,
        "project_keywords": state.project_keywords,
        "project_infos": state.project_infos,
        "context_log": state.context_log,
        "stored_plan": state.plan,
        "next_step_index": step_index,
        "plan_position": state.plan_position,
    }
    return json.dumps(context, ensure_ascii=False, indent=2)


def run_planner(user_input: str, state: ProjectState, step_index: Optional[int]) -> Dict[str, Any]:
    """
    Ruft den Planner-Agenten auf und aktualisiert den Projektstate.
    step_index:
      - None: Plan neu erstellen (falls keiner vorhanden) und Prompt fuer ersten Schritt liefern.
      - int: Prompt fuer genau diesen Schritt basierend auf stored_plan erzeugen.
    """
    content = _build_planner_context(user_input, state, step_index)
    data = call_agent_with_repair(
        agent_name="Planner",
        system_prompt=str(PLANNER_SYSTEM_PROMPT),
        user_content=content,
        schema_hint=PLANNER_JSON_SCHEMA_HINT,
        model=DEFAULT_MODEL,
        expected_keys=["plan", "prompts_for_executor", "clarification"],
        model_cls=PlannerResponse,
    )

    if isinstance(data, PlannerResponse):
        summaries = data.summaries
        state.chat_summary = summaries.chat_summary or state.chat_summary
        state.project_summary = summaries.project_summary or state.project_summary
        state.project_keywords = summaries.project_keywords or state.project_keywords
        state.project_infos = data.project_infos or state.project_infos
        if data.plan:
            state.plan = data.plan
        state.plan_position = data.plan_position if data.plan_position is not None else state.plan_position
        state.save()
        return data.model_dump()

    # Fallback, falls kein Pydantic-Objekt
    summaries = data.get("summaries", {}) or {}
    state.chat_summary = summaries.get("chat_summary", state.chat_summary)
    state.project_summary = summaries.get("project_summary", state.project_summary)
    state.project_keywords = summaries.get("project_keywords", state.project_keywords)
    state.project_infos = data.get("project_infos", state.project_infos)
    new_plan = data.get("plan")
    if isinstance(new_plan, list) and new_plan:
        state.plan = new_plan
    if "plan_position" in data:
        try:
            state.plan_position = int(data["plan_position"])
        except Exception:
            pass

    state.save()
    return data
