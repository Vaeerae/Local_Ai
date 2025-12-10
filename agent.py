# self_expanding_agent.py
import importlib
import json
import os
import sys
import traceback
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

import ollama  # erwartet lokales ollama

ENCODING = "utf-8-sig"

BASE_DIR = os.path.dirname(__file__)
STATE_PATH = os.path.join(BASE_DIR, "agent_state.json")
TOOLS_META_PATH = os.path.join(BASE_DIR, "tools.json")
TOOLS_PY_PATH = os.path.join(BASE_DIR, "tools.py")

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "ministral-3:14b")
EXECUTOR_MODEL = os.environ.get("EXECUTOR_MODEL", DEFAULT_MODEL)
VALIDATOR_MODEL = os.environ.get("VALIDATOR_MODEL", DEFAULT_MODEL)

MAX_PLAN_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "8"))
MAX_EXECUTOR_RETRIES = int(os.environ.get("EXECUTOR_MAX_RETRIES", "3"))
MAX_JSON_REPAIR_RETRIES = int(os.environ.get("JSON_REPAIR_RETRIES", "2"))


# ====================== SYSTEM PROMPTS (Dateipfade) ======================

PLANNER_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts", "planner_system_prompt.txt")
EXECUTOR_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts", "executor_system_prompt.txt")
VALIDATOR_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts", "validator_system_prompt.txt")


# ====================== JSON-SCHEMA-HINWEISE FÜR REPAIR ======================

PLANNER_JSON_SCHEMA_HINT = """\
{
  "clarification": {
    "needed": false,
    "question": ""
  },
  "plan": [],
  "summaries": {
    "chat_summary": "",
    "project_summary": "",
  },
  "user_message": "",
  "prompts_for_executor": [],
  "project_infos": []
}
"""

EXECUTOR_JSON_SCHEMA_HINT = """\
{
  "picked_prompt": "",
  "actions": [
    {
      "tool_name": "",
      "args": {}
    }
  ],
  "new_tools": [
    {
      "nameTool": "",
      "beschreib": "",
      "args": "",
      "ergebniss": "",
      "python_code": ""
    }
  ],
  "tests": [
    {
      "tool_name": "",
      "test_code": ""
    }
  ],
  "execution_notes": "",
  "next_prompt": ""
}
"""

VALIDATOR_JSON_SCHEMA_HINT = """\
{
  "approved": false,
  "reason": "",
  "fix_prompt": ""
}
"""


# ====================== HILFSFUNKTIONEN ======================

def safe_open(path: str, mode: str = "r"):
    return open(path, mode, encoding=ENCODING)


def load_text(path: str) -> str:
    with safe_open(path, "r") as f:
        return f.read()


def extract_json_content(text: str) -> str:
    """
    Versucht, einen JSON-Block aus einem Model-Output zu extrahieren.
    Toleriert:
    - Markdown-```-Blöcke (z. B. ```json {...} ```)
    - Triple-Quote-Blöcke (z. B. \"\"\"json {...} \"\"\")
    - einfache Triple-Quotes (''') ebenfalls
    """
    if text is None:
        return ""

    text = str(text).strip()

    # 1) Triple-Quotes """...""" mit optional "json" Prefix
    if '"""' in text:
        parts = text.split('"""')
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate

    # 2) Triple-Quotes '''...''' mit optional "json" Prefix
    if "'''" in text:
        parts = text.split("'''")
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate

    # 3) Reiner Triple-Quote-Wrapper """..."""
    if text.startswith('"""') and text.endswith('"""'):
        inner = text[3:-3].strip()
        if inner.lower().startswith("json"):
            inner = inner[4:].strip()
        if inner.startswith("{") and inner.endswith("}"):
            return inner

    if text.startswith("'''") and text.endswith("'''"):
        inner = text[3:-3].strip()
        if inner.lower().startswith("json"):
            inner = inner[4:].strip()
        if inner.startswith("{") and inner.endswith("}"):
            return inner

    # 4) Markdown-```-Blöcke
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate

    # 5) Fallback: äusserstes { ... }-Paar extrahieren
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text.strip()


def call_model_streaming(system_prompt: str, user_content: str, model: str = DEFAULT_MODEL) -> str:
    """
    Aufruf von ollama.chat mit Streaming-Ausgabe.
    system_prompt kann Pfad oder reiner Prompt-Text sein.
    Gibt den gesamten vom Modell generierten Text zurück.
    """
    sys_prompt_text = system_prompt
    try:
        if os.path.exists(system_prompt):
            sys_prompt_text = load_text(system_prompt)
    except Exception:
        sys_prompt_text = system_prompt

    print(f"\n[Model {model}] Starte Streaming-Antwort …")
    messages = [
        {"role": "system", "content": sys_prompt_text},
        {"role": "user", "content": user_content},
    ]

    full_content_parts: List[str] = []

    try:
        for chunk in ollama.chat(model=model, messages=messages, tools= [], stream=True):
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                full_content_parts.append(piece)
                print(piece, end="", flush=True)
    except Exception as exc:
        print(f"\n[WARN] Streaming-Fehler: {exc}", file=sys.stderr)

    print()  # Zeilenumbruch nach Stream
    return "".join(full_content_parts).strip()


def ensure_tools_files_exist() -> None:
    """Lege tools.py und tools.json an, falls sie fehlen."""
    if not os.path.exists(TOOLS_PY_PATH):
        with safe_open(TOOLS_PY_PATH, "w") as f:
            f.write(
                "# Automatisch generiertes Tools-Modul\n\n"
                "TOOL_REGISTRY = {}\n"
            )

    if not os.path.exists(TOOLS_META_PATH):
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
    - tools.json: Metadaten werden angehängt, aber nur wenn der Name nicht bereits existiert.
    - tools.py: Python-Code wird angehängt, Registry-Eintrag wird gesetzt.
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

            # Metadaten nur ergänzen, wenn der Name noch nicht existiert
            if name not in existing_names:
                meta_entry = {
                    "nameTool": name,
                    "beschreib": tool.get("beschreib", ""),
                    "args": tool.get("args", ""),
                    "ergebniss": tool.get("ergebniss", ""),
                }
                meta.append(meta_entry)
                existing_names.add(name)

            # Code in tools.py anhängen
            f_py.write("\n\n")
            f_py.write(code.strip())
            f_py.write("\n")
            f_py.write(f'TOOL_REGISTRY["{name}"] = {name}\n')

    save_tools_meta(meta)


# ====================== GENERISCHER AGENT-CALL MIT JSON-REPAIR ======================

def call_agent_with_repair(
    agent_name: str,
    system_prompt: str,
    user_content: str,
    schema_hint: str,
    model: str,
) -> Dict[str, Any]:
    """
    Ruft einen Agenten (Planner/Executor/Validator) mit Streaming auf.
    Wenn die Antwort kein gültiges JSON ist, wird ein Reparatur-Prompt erzeugt,
    der dem Modell den Fehler (Traceback/JSONDecodeError) und die eigene Roh-Antwort
    sowie das exakte JSON-Schema mitteilt. Es wird bis zu MAX_JSON_REPAIR_RETRIES mal versucht.
    """
    attempt = 0
    last_raw = ""
    last_error = None

    while attempt < MAX_JSON_REPAIR_RETRIES:
        attempt += 1
        print(f"\n[{agent_name}] Modell-Aufruf (Versuch {attempt}) …")

        raw = call_model_streaming(system_prompt, user_content, model=model)
        last_raw = raw
        cleaned = extract_json_content(raw)

        try:
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as exc:
            last_error = exc
            err_text = "".join(traceback.format_exception_only(type(exc), exc))
            print(f"\n[ERROR] {agent_name}-JSON konnte nicht geparst werden:", err_text, file=sys.stderr)
            print("==== Roh-Output des Modells ====", file=sys.stderr)
            print(raw, file=sys.stderr)
            print("==== Ende Roh-Output ====", file=sys.stderr)

            # Reparatur-Prompt bauen: Modell soll seine eigene Antwort prüfen und korrigieren
            repair_prompt = (
                f"Deine letzte Antwort als {agent_name}-Agent war KEIN gültiges JSON und "
                f"hat einen JSONDecodeError ausgelöst.\n\n"
                f"Fehlermeldung (Traceback-Auszug):\n{err_text}\n\n"
                "Hier ist deine komplette vorherige Antwort:\n"
                "----- BEGINN DEINER ANTWORT -----\n"
                f"{raw}\n"
                "----- ENDE DEINER ANTWORT -----\n\n"
                "Bitte analysiere deine eigene Antwort, finde die JSON-Fehler und gib JETZT "
                "AUSSCHLIESSLICH ein einziges, strikt gültiges JSON-Objekt zurück.\n"
                "- KEIN zusätzlicher Text\n"
                "- KEINE Erklärungen\n"
                "- KEIN Markdown\n"
                "- KEINE Kommentare\n\n"
                "Halte dich EXAKT an die folgende Struktur (Feldnamen und Aufbau):\n"
                f"{schema_hint}\n"
            )

            # Nächster Versuch nutzt den Reparatur-Prompt
            user_content = repair_prompt

    # Wenn nach allen Versuchen kein gültiges JSON vorliegt -> harter Fehler
    raise RuntimeError(
        f"{agent_name}-Agent lieferte wiederholt kein gültiges JSON. "
        f"Letzter Fehler: {last_error}\nLetzte Antwort:\n{last_raw}"
    )


# ====================== STATE ======================

@dataclass
class ProjectState:
    chat_summary: str = ""
    project_summary: str = ""
    project_keywords: List[str] = field(default_factory=list)
    project_infos: List[str] = field(default_factory=list)

    @staticmethod
    def load(path: str) -> "ProjectState":
        if not os.path.exists(path):
            return ProjectState()
        with safe_open(path, "r") as f:
            data = json.load(f)
        return ProjectState(
            chat_summary=data.get("chat_summary", ""),
            project_summary=data.get("project_summary", ""),
            project_keywords=data.get("project_keywords", []),
            project_infos=data.get("project_infos", []),
        )

    def save(self, path: str) -> None:
        with safe_open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


# ====================== PLANNER ======================

def run_planner(user_input: str, state: ProjectState) -> Dict[str, Any]:
    context = (
        "Bisherige Projektzusammenfassung:\n"
        f"chat_summary: {state.chat_summary}\n"
        f"project_summary: {state.project_summary}\n"
        f"project_keywords: {', '.join(state.project_keywords)}\n"
        f"project_infos: {state.project_infos}\n\n"
        "Nutzerziel:\n"
        f"{user_input}"
    )

    data = call_agent_with_repair(
        agent_name="Planner",
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_content=context,
        schema_hint=PLANNER_JSON_SCHEMA_HINT,
        model=DEFAULT_MODEL,
    )

    summaries = data.get("summaries", {})
    state.chat_summary = summaries.get("chat_summary", state.chat_summary)
    state.project_summary = summaries.get("project_summary", state.project_summary)
    state.project_keywords = summaries.get("project_keywords", state.project_keywords)
    state.project_infos = data.get("project_infos", state.project_infos)

    state.save(STATE_PATH)

    return data


# ====================== EXECUTOR & VALIDATOR ======================

def run_executor(prompt_for_executor: str, tools_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ruft den Executor-Agenten auf. Übergibt ihm den Arbeits-Prompt und die bekannten Tools.
    Nutzt JSON-Repair-Mechanismus bei fehlerhafter Antwort.
    """
    payload = {
        "executor_task": prompt_for_executor,
        "known_tools": tools_meta,
        "hint": (
            "Denke daran, dass du selbst keinen Code ausführst. "
            "Du definierst nur neue Tools und planst konkrete Funktionsaufrufe."
        ),
    }

    user_content = json.dumps(payload, indent=2, ensure_ascii=False)

    data = call_agent_with_repair(
        agent_name="Executor",
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=EXECUTOR_JSON_SCHEMA_HINT,
        model=EXECUTOR_MODEL,
    )
    return data


def execute_actions(actions: List[Dict[str, Any]], tool_funcs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Führt die geplanten Funktionsaufrufe aus.
    Bricht beim ersten Fehler ab.
    """
    outputs: List[Any] = []

    for idx, action in enumerate(actions):
        name = action.get("tool_name")
        args = action.get("args", {}) or {}
        func = tool_funcs.get(name)

        if func is None:
            return {
                "success": False,
                "error": f"Tool '{name}' nicht im TOOL_REGISTRY gefunden.",
                "traceback": "",
                "outputs": outputs,
            }

        try:
            result = func(**args)
            outputs.append({"tool_name": name, "result": result})
        except Exception:
            return {
                "success": False,
                "error": f"Tool '{name}' hat eine Exception ausgelöst.",
                "traceback": traceback.format_exc(),
                "outputs": outputs,
            }

    return {
        "success": True,
        "error": "",
        "traceback": "",
        "outputs": outputs,
    }


def run_validator(step_description: str,
                  executor_prompt: str,
                  tools_meta: List[Dict[str, Any]],
                  execution_result: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "step_description": step_description,
        "executor_prompt": executor_prompt,
        "tools": tools_meta,
        "execution": {
            "success": bool(execution_result.get("success")),
            "error": execution_result.get("error", ""),
            "traceback": execution_result.get("traceback", ""),
        },
    }

    user_content = json.dumps(payload, indent=2, ensure_ascii=False)

    data = call_agent_with_repair(
        agent_name="Validator",
        system_prompt=VALIDATOR_SYSTEM_PROMPT,
        user_content=user_content,
        schema_hint=VALIDATOR_JSON_SCHEMA_HINT,
        model=VALIDATOR_MODEL,
    )
    return data


# ====================== ORCHESTRATOR ======================

def run_full_cycle(user_input: str) -> None:
    state = ProjectState.load(STATE_PATH)

    print("\n[Planner] Plane Aufgabe …")
    planner_reply = run_planner(user_input, state)

    clarification = planner_reply.get("clarification", {})
    if clarification.get("needed"):
        print("\n[Planner] Rückfrage:")
        print(clarification.get("question", ""))
        return

    plan: List[str] = planner_reply.get("plan", []) or []
    prompts_for_executor: List[str] = planner_reply.get("prompts_for_executor", []) or []

    print("\n[Planner] Plan:")
    for i, step in enumerate(plan, start=1):
        print(f"  {i}. {step}")

    print("\n[Planner] Nachricht an User:")
    print(planner_reply.get("user_message", ""))

    tools_meta = load_tools_meta()

    for idx, step in enumerate(plan):
        print("\n" + "=" * 70)
        print(f"[Orchestrator] Bearbeite Plan-Schritt {idx + 1}/{len(plan)}:")
        print(step)

        if idx < len(prompts_for_executor):
            base_prompt = prompts_for_executor[idx]
        else:
            base_prompt = f"Führe folgenden Plan-Schritt aus: {step}"

        executor_prompt = base_prompt
        attempt = 0

        while attempt < MAX_EXECUTOR_RETRIES:
            attempt += 1
            print(f"\n[Executor] Versuch {attempt} für diesen Schritt …")

            executor_reply = run_executor(executor_prompt, tools_meta)

            picked_prompt = executor_reply.get("picked_prompt", "")
            actions = executor_reply.get("actions", []) or []
            new_tools = executor_reply.get("new_tools", []) or []
            tests = executor_reply.get("tests", []) or []
            execution_notes = executor_reply.get("execution_notes", "")

            print(f"[Executor] picked_prompt: {picked_prompt}")
            if execution_notes:
                print("[Executor] execution_notes:", execution_notes)

            if new_tools:
                print(f"[Executor] Neue Tools vorgeschlagen: {[t.get('nameTool') for t in new_tools]}")
                append_new_tools(new_tools)
                tools_meta = load_tools_meta()

            tool_funcs = load_tool_functions()

            print(f"[Executor] Führe {len(actions)} Aktionen aus …")
            execution_result = execute_actions(actions, tool_funcs)

            print("[Executor] execution_result.success:", execution_result["success"])
            if execution_result["error"]:
                print("[Executor] error:", execution_result["error"])
            if execution_result["traceback"]:
                print("[Executor] traceback:", execution_result["traceback"])

            validator_reply = run_validator(
                step_description=step,
                executor_prompt=executor_prompt,
                tools_meta=tools_meta,
                execution_result=execution_result,
            )

            approved = bool(validator_reply.get("approved"))
            reason = validator_reply.get("reason", "")
            fix_prompt = validator_reply.get("fix_prompt", "")

            print("[Validator] approved:", approved)
            print("[Validator] reason:", reason)

            if approved:
                print("[Orchestrator] Schritt akzeptiert, gehe zum nächsten Planpunkt.")
                break

            if not fix_prompt:
                print("[Orchestrator] Validator hat keinen fix_prompt geliefert, breche diesen Schritt ab.")
                break

            print("[Orchestrator] Validator fordert Korrektur. Neuer Prompt für Executor.")
            executor_prompt = fix_prompt

        else:
            print("[Orchestrator] Maximale Anzahl von Executor-Versuchen erreicht, fahre mit nächstem Schritt fort.")

    print("\n[Orchestrator] Plan-Durchlauf abgeschlossen.")


def main() -> None:
    if not os.path.exists(STATE_PATH):
        print("[INFO] Keine bestehende agent_state.json gefunden, es wird ein neuer Projektzustand angelegt.")
        ProjectState().save(STATE_PATH)

    print("Selbst-erweiternder Multi-Agent (Planner / Executor / Validator)")
    print("Gib eine Aufgabe ein. Mit 'exit' oder 'quit' beenden.\n")

    while True:
        try:
            user_input = input("Du: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTschüss.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Tschüss.")
            break

        if not user_input:
            continue

        run_full_cycle(user_input)


if __name__ == "__main__":
    main()
