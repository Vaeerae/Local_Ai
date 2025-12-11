import json
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List

from config import ERRORS_DIR, MAX_EXECUTOR_RETRIES
from executor_agent import run_executor
from fast_tool import run_fast_tool
from io_utils import ensure_dir, safe_open
from planner_agent import run_planner
from state import ProjectState
from tools_manager import append_new_tools, load_tool_functions, load_tools_meta
from validator_agent import run_validator


def execute_actions(actions: List[Dict[str, Any]], tool_funcs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Faehrt die geplanten Funktionsaufrufe aus. Bricht beim ersten Fehler ab.
    """
    outputs: List[Any] = []

    for action in actions:
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
                "error": f"Tool '{name}' hat eine Exception ausgeloest.",
                "traceback": traceback.format_exc(),
                "outputs": outputs,
            }

    return {
        "success": True,
        "error": "",
        "traceback": "",
        "outputs": outputs,
    }


def run_full_cycle(user_input: str) -> None:
    state = ProjectState.load()

    # Reset Plan, wenn neuer User-Prompt
    if state.user_prompt and user_input != state.user_prompt:
        state.plan = []
        state.plan_position = 0
        state.context_log = []
        state.project_infos = []
    state.user_prompt = user_input

    # Schritt 0: Falls kein Plan existiert, jetzt erstellen und Prompt fuer ersten Schritt holen
    if not state.plan:
        print("\n[Planner] Plane Aufgabe")
        planner_reply = run_planner(user_input, state, step_index=None)

        clarification = planner_reply.get("clarification", {}) or {}
        if clarification.get("needed"):
            print("\n[Planner] Rueckfrage:")
            print(clarification.get("question", ""))
            return

        state.plan = planner_reply.get("plan", []) or []
        state.plan_position = 0
        state.save()
    else:
        print("\n[Planner] Fortsetzen mit bestehendem Plan.")

    print("\n[Planner] Plan:")
    for i, step in enumerate(state.plan, start=1):
        marker = " <= naechster" if (i - 1) == state.plan_position else ""
        print(f"  {i}. {step}{marker}")

    tools_meta = load_tools_meta()
    file_overview = _build_file_overview()

    while state.plan_position < len(state.plan):
        step_idx = state.plan_position
        step = state.plan[step_idx]

        print("\n" + "=" * 70)
        print(f"[Orchestrator] Bearbeite Plan-Schritt {step_idx + 1}/{len(state.plan)}:")
        print(step)

        # Planner liefert frischen Prompt fuer genau diesen Schritt (unter Nutzung des gespeicherten Plans/Contexts)
        planner_reply = run_planner(state.user_prompt, state, step_index=step_idx)
        clarification = planner_reply.get("clarification", {}) or {}
        if clarification.get("needed"):
            print("[Planner] Rueckfrage statt Prompt:")
            print(clarification.get("question", ""))
            break

        prompts_for_executor: List[str] = planner_reply.get("prompts_for_executor", []) or []
        executor_prompt = prompts_for_executor[0] if prompts_for_executor else f"Fuehre folgenden Plan-Schritt aus: {step}"

        attempt = 0
        last_execution_result: Dict[str, Any] = {}
        approved = False

        while attempt < MAX_EXECUTOR_RETRIES:
            attempt += 1
            print(f"\n[Executor] Versuch {attempt} fuer diesen Schritt")

            executor_reply = run_executor(
                user_prompt=state.user_prompt,
                plan=state.plan,
                plan_position=state.plan_position,
                current_step=step,
                executor_prompt=executor_prompt,
                tools_meta=tools_meta,
                file_overview=file_overview,
                context_log=state.context_log,
            )

            picked_prompt = executor_reply.get("picked_prompt", "")
            actions = executor_reply.get("actions", []) or []
            new_tools = executor_reply.get("new_tools", []) or []
            execution_notes = executor_reply.get("execution_notes", "")
            fast_infos = bool(executor_reply.get("fast_infos"))
            fast_tool_name = executor_reply.get("fast_tool", "")
            fast_args = executor_reply.get("fast_args", {}) or {}

            print(f"[Executor] picked_prompt: {picked_prompt}")
            if execution_notes:
                print("[Executor] execution_notes:", execution_notes)

            if new_tools:
                print(f"[Executor] Neue Tools vorgeschlagen: {[t.get('nameTool') for t in new_tools]}")
                append_new_tools(new_tools)
                tools_meta = load_tools_meta()
                file_overview = _build_file_overview()

            tool_funcs = load_tool_functions()

            # Schnelle Info-Beschaffung vor eigentlicher Aktion
            if fast_infos and fast_tool_name:
                print(f"[Executor] Fuehre Fast-Tool '{fast_tool_name}' aus")
                fast_result = run_fast_tool(fast_tool_name, fast_args, tool_funcs)
                last_execution_result = fast_result
                if not fast_result.get("success"):
                    print("[Executor] Fast-Tool fehlgeschlagen, Prompt wird mit Fehler erneut versucht.")
                    executor_prompt = executor_reply.get("next_prompt") or (
                        executor_prompt
                        + f"\nFast-Tool '{fast_tool_name}' fehlgeschlagen: {fast_result.get('error')}"
                    )
                    continue
                # Erfolg: ergaenze Kontextlog mit Ergebnis
                state.context_log.append(
                    json.dumps(
                        {"fast_tool": fast_tool_name, "outputs": fast_result.get("outputs", [])},
                        ensure_ascii=False,
                    )
                )
                state.save()

            print(f"[Executor] Fuehre {len(actions)} Aktionen aus")
            execution_result = execute_actions(actions, tool_funcs)
            last_execution_result = execution_result
            file_overview = _build_file_overview()

            print("[Executor] execution_result.success:", execution_result["success"])
            if execution_result["error"]:
                print("[Executor] error:", execution_result["error"])
            if execution_result["traceback"]:
                print("[Executor] traceback:", execution_result["traceback"])

            validator_reply = run_validator(
                user_prompt=state.user_prompt,
                plan=state.plan,
                plan_position=state.plan_position,
                step_description=step,
                executor_prompt=executor_prompt,
                tools_meta=tools_meta,
                execution_result=execution_result,
                file_overview=file_overview,
                context_log=state.context_log,
            )

            approved = bool(validator_reply.get("approved"))
            reason = validator_reply.get("reason", "")
            fix_prompt = validator_reply.get("fix_prompt", "")

            print("[Validator] approved:", approved)
            print("[Validator] reason:", reason)

            if approved:
                print("[Orchestrator] Schritt akzeptiert, gehe zum naechsten Planpunkt.")
                break

            if not fix_prompt:
                # Fallback: erweitere bestehenden Prompt um Fehlerdetails
                err_block = (
                    f"Vorheriger Lauf fehlgeschlagen. Error: {execution_result.get('error','')}. "
                    f"Traceback: {execution_result.get('traceback','')}"
                )
                executor_prompt = executor_prompt + "\n" + err_block
                print("[Orchestrator] Kein fix_prompt, benutze Fehlerdetails als neuen Prompt.")
            else:
                print("[Orchestrator] Validator fordert Korrektur. Neuer Prompt fuer Executor.")
                executor_prompt = fix_prompt

        else:
            print("[Orchestrator] Maximale Anzahl von Executor-Versuchen erreicht, Fehler wird protokolliert und naechster Schritt gestartet.")
            _write_error_log(step_idx, step, executor_prompt, last_execution_result, state)

        # Kontext fortschreiben
        _append_context(state, step, approved, last_execution_result)
        state.plan_position += 1
        state.save()

    print("\n[Orchestrator] Plan-Durchlauf abgeschlossen.")


def _write_error_log(step_idx: int, step: str, prompt: str, execution_result: Dict[str, Any], state: ProjectState) -> None:
    ensure_dir(ERRORS_DIR)
    payload = {
        "step_index": step_idx,
        "step_description": step,
        "prompt": prompt,
        "execution_result": execution_result,
        "state_snapshot": {
            "user_prompt": state.user_prompt,
            "chat_summary": state.chat_summary,
            "project_summary": state.project_summary,
            "project_keywords": state.project_keywords,
            "project_infos": state.project_infos,
            "context_log": state.context_log,
            "plan": state.plan,
            "plan_position": state.plan_position,
        },
    }
    path = Path(ERRORS_DIR) / f"step_{step_idx + 1}.json"
    with safe_open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[Orchestrator] Fehlerprotokoll geschrieben: {path}")


def _append_context(state: ProjectState, step: str, approved: bool, execution_result: Dict[str, Any]) -> None:
    note = {
        "step": step,
        "approved": approved,
        "error": execution_result.get("error", ""),
        "traceback": execution_result.get("traceback", ""),
        "outputs": execution_result.get("outputs", []),
    }
    state.context_log.append(json.dumps(note, ensure_ascii=False))


def _build_file_overview() -> List[str]:
    paths: List[str] = []
    base = Path.cwd()
    for root, dirs, files in os.walk(base):
        # skip envs or hidden heavy dirs
        if any(part.startswith(".") for part in Path(root).parts):
            continue
        for fname in files:
            rel = Path(root, fname).relative_to(base)
            paths.append(str(rel))
    return sorted(paths)
