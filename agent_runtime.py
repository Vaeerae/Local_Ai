import json
import traceback
from typing import Any, Dict, Iterable, Optional, Type

from pydantic import BaseModel, ValidationError

from config import MAX_JSON_REPAIR_RETRIES
from json_utils import build_repair_prompt, parse_json_with_fallback
from llm_client import call_model_streaming


def _has_expected_keys(data: Dict[str, Any], expected: Iterable[str] | None) -> bool:
    if not expected:
        return True
    return any(key in data for key in expected)


def _coerce_pydantic(model_cls: Type[BaseModel], data: Dict[str, Any]):
    try:
        return model_cls.model_validate(data)
    except ValidationError:
        return None


def call_agent_with_repair(
    agent_name: str,
    system_prompt: str,
    user_content: str,
    schema_hint: str,
    model: str,
    expected_keys: Iterable[str] | None = None,
    model_cls: Optional[Type[BaseModel]] = None,
) -> Any:
    """
    Calls an agent with streaming and retries if JSON parsing fails.
    Returns a dict or pydantic model instance if model_cls is provided.
    """
    attempt = 0
    last_raw = ""
    last_error = None
    prompt = user_content

    while attempt < MAX_JSON_REPAIR_RETRIES:
        attempt += 1
        print(f"\n[{agent_name}] Modell-Aufruf (Versuch {attempt})")

        raw = call_model_streaming(system_prompt, prompt, model=model)
        last_raw = raw

        data = parse_json_with_fallback(raw, expected_keys=expected_keys)
        if data and _has_expected_keys(data, expected_keys):
            if model_cls:
                coerced = _coerce_pydantic(model_cls, data)
                if coerced:
                    return coerced
            return data

        try:
            data = json.loads(raw)
            if model_cls:
                coerced = _coerce_pydantic(model_cls, data)
                if coerced:
                    return coerced
            return data
        except json.JSONDecodeError as exc:
            last_error = exc
            err_text = "".join(traceback.format_exception_only(type(exc), exc))
            print(f"\n[ERROR] {agent_name}-JSON konnte nicht geparst werden: {err_text}")
            print("==== Roh-Output des Modells ====")
            print(raw)
            print("==== Ende Roh-Output ====")
            prompt = build_repair_prompt(agent_name, err_text, raw, schema_hint)

    raise RuntimeError(
        f"{agent_name}-Agent lieferte wiederholt kein gueltiges JSON. "
        f"Letzter Fehler: {last_error}\nLetzte Antwort:\n{last_raw}"
    )
