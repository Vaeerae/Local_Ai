import json
import re
from typing import Any, Dict, Iterable


def extract_json_content(text: str) -> str:
    """
    Best-effort extraction of a JSON object from model text.
    Handles code fences, triple quotes and falls back to outermost braces.
    """
    if text is None:
        return ""

    text = str(text).strip()
    if not text:
        return ""

    fences = ['```', '"""', "'''"]
    for fence in fences:
        if fence in text:
            parts = text.split(fence)
            for part in parts:
                candidate = part.strip()
                if not candidate:
                    continue
                if candidate.lower().startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    return candidate

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text


def _strip_trailing_commas(candidate: str) -> str:
    candidate = re.sub(r",\s*}", "}", candidate)
    candidate = re.sub(r",\s*]", "]", candidate)
    return candidate


def _scan_for_keys(text: str, expected_keys: Iterable[str]) -> Dict[str, Any]:
    """
    Lightweight text analysis to recover values for known keys from malformed JSON output.
    Looks for 'key: value' or '"key": value' patterns line by line.
    """
    recovered: Dict[str, Any] = {}
    lines = text.splitlines()
    for key in expected_keys:
        pattern = re.compile(rf'"?{re.escape(key)}"?\s*[:=]\s*(.+)', re.IGNORECASE)
        for line in lines:
            match = pattern.search(line)
            if not match:
                continue
            raw_val = match.group(1).strip().rstrip(",")
            recovered[key] = _best_effort_json_value(raw_val)
            break
    return recovered


def _best_effort_json_value(raw_val: str) -> Any:
    """
    Tries to coerce a raw value fragment into a JSON-compatible Python value.
    """
    # Simple literals
    lowered = raw_val.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered == "null":
        return None

    # Try number
    try:
        if "." in raw_val:
            return float(raw_val)
        return int(raw_val)
    except ValueError:
        pass

    # Try JSON decode
    try:
        return json.loads(raw_val)
    except Exception:
        pass

    # Fallback to string without surrounding quotes
    return raw_val.strip('"\'' )


def parse_json_with_fallback(raw: str, expected_keys: Iterable[str] | None = None) -> Dict[str, Any]:
    """
    Parse model output into JSON with multiple fallback strategies:
    - Extract JSON block from text
    - Remove trailing commas
    - Try repairing missing closing brace
    - Remove newlines and retry (with/ohne zusaetzliche Klammer)
    - Try json.loads with strict=False
    - Recover known keys from text if nothing else works
    """
    if raw is None:
        return {}

    candidate = extract_json_content(raw)
    candidate = _strip_trailing_commas(candidate)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Retry with appended closing brace
    try:
        return json.loads(candidate.rstrip() + "}")
    except json.JSONDecodeError:
        pass

    # Remove newlines and retry
    compact = "".join(candidate.splitlines())
    try:
        return json.loads(compact)
    except json.JSONDecodeError:
        pass

    # Remove newlines and append closing brace
    try:
        return json.loads(compact.rstrip() + "}")
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(candidate, strict=False)
    except Exception:
        pass

    if expected_keys:
        return _scan_for_keys(raw, expected_keys)

    return {}


def build_repair_prompt(agent_name: str, error_text: str, raw: str, schema_hint: str) -> str:
    return (
        f"Deine letzte Antwort als {agent_name}-Agent war kein gueltiges JSON und hat einen JSONDecodeError ausgeloest.\n\n"
        f"Fehlermeldung:\n{error_text}\n\n"
        "Komplette letzte Antwort:\n"
        "-----\n"
        f"{raw}\n"
        "-----\n\n"
        "Analysiere deine Antwort und gib JETZT ausschliesslich ein einziges, strikt gueltiges JSON-Objekt zurueck.\n"
        "- Kein Text ausserhalb des JSON\n"
        "- Kein Markdown\n"
        "- Keine Kommentare\n\n"
        "Struktur, an die du dich halten musst:\n"
        f"{schema_hint}\n"
    )
