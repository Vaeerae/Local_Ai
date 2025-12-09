import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple

import ollama
from pydantic import BaseModel, Field, ValidationError

ENCODING = "utf-8-sig"
STATE_PATH = os.path.join(os.path.dirname(__file__), "agent_state.json")
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "base_system_prompt.txt")
DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "ministral-3:14b")
MAX_AUTO_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "8"))


def load_text(path: str) -> str:
    with open(path, "r", encoding=ENCODING) as f:
        return f.read()


def extract_json_content(text: str) -> str:
    """Extract JSON payload, tolerating markdown fences."""
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
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


def safe_open(path: str, mode: str = "r"):
    return open(path, mode, encoding=ENCODING)


@dataclass
class AgentState:
    chat_summary: str
    project_summary: str
    project_keywords: List[str]
    prompt_extension: str
    known_tools: List[Dict[str, Any]]
    plan_queue: List[str]

    @staticmethod
    def load(path: str) -> "AgentState":
        with safe_open(path, "r") as f:
            data = json.load(f)
        return AgentState(
            chat_summary=data.get("chat_summary", ""),
            project_summary=data.get("project_summary", ""),
            project_keywords=data.get("project_keywords", []),
            prompt_extension=data.get("prompt_extension", ""),
            known_tools=data.get("known_tools", []),
            plan_queue=data.get("plan_queue", []),
        )

    def save(self, path: str) -> None:
        with safe_open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


class ToolResult(BaseModel):
    success: bool
    message: str
    output: Any = None
    error: str = ""


def create_directory(path: str) -> Dict[str, Any]:
    try:
        os.makedirs(path, exist_ok=True)
        return ToolResult(success=True, message=f"Created directory {path}", output=None).model_dump()
    except Exception as exc:
        return ToolResult(success=False, message="Failed to create directory", error=str(exc)).model_dump()


def write_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    try:
        if os.path.exists(path) and not overwrite:
            return ToolResult(success=False, message="File exists and overwrite is False").model_dump()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with safe_open(path, "w") as f:
            f.write(content)
        return ToolResult(success=True, message=f"Wrote file {path}", output=len(content)).model_dump()
    except Exception as exc:
        return ToolResult(success=False, message="Failed to write file", error=str(exc)).model_dump()


def run_shell(command: str, workdir: str = ".") -> Dict[str, Any]:
    import subprocess

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
        return ToolResult(
            success=success,
            message="Command executed" if success else f"Command failed ({proc.returncode})",
            output=proc.stdout.strip(),
            error=proc.stderr.strip(),
        ).model_dump()
    except Exception as exc:
        return ToolResult(success=False, message="Exception during command", error=str(exc)).model_dump()


TOOLS = {
    "create_directory": create_directory,
    "write_file": write_file,
    "run_shell": run_shell,
}


class ModelReply(BaseModel):
    clarification: Dict[str, Any]
    plan: List[str]
    action: Dict[str, Any]
    self_review: Dict[str, Any]
    summaries: Dict[str, Any]
    user_message: str = Field(default="")


def build_system_prompt(state: AgentState) -> str:
    base = load_text(PROMPT_PATH)
    if state.prompt_extension:
        base += "\n\n# Prompt extension\n" + state.prompt_extension
    if state.known_tools:
        base += "\n\n# Known tool definitions\n" + json.dumps(state.known_tools, indent=2)
    return base


def stream_model(messages: List[Dict[str, str]]) -> str:
    content_parts: List[str] = []
    try:
        print("Model:", end=" ", flush=True)
        for chunk in ollama.chat(model=DEFAULT_MODEL, messages=messages, stream=True):
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                content_parts.append(piece)
                print(piece, end="", flush=True)
        print()
    except Exception as exc:
        print(f"\n[stream error: {exc}]", file=sys.stderr)
    return "".join(content_parts).strip()


def parse_model_reply(raw_text: str, state: AgentState) -> ModelReply:
    cleaned = extract_json_content(raw_text)
    try:
        data = json.loads(cleaned)
        return ModelReply(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        fallback = {
            "clarification": {"needed": False, "question": ""},
            "plan": [],
            "action": {
                "mode": "none",
                "tool_name": "",
                "tool_arguments": {},
                "new_tool": {
                    "name": "",
                    "kind": "python_macro",
                    "description": "",
                    "arguments_schema": {},
                    "template": ""
                },
                "prompt_extension_update": ""
            },
            "self_review": {"test_description": "parse reply", "passed": False, "fix_hint": str(exc)},
            "summaries": {
                "chat_summary": state.chat_summary,
                "project_summary": state.project_summary,
                "project_keywords": state.project_keywords,
            },
            "user_message": "Model response could not be parsed; please retry.",
        }
        return ModelReply(**fallback)


def call_model(state: AgentState, user_input: str) -> Tuple[ModelReply, str]:
    system_prompt = build_system_prompt(state)
    plan_hint = "\nPending plan: " + json.dumps(state.plan_queue) if state.plan_queue else ""
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"Chat summary: {state.chat_summary}\nProject summary: {state.project_summary}\nKeywords: {', '.join(state.project_keywords)}{plan_hint}",
        },
        {"role": "user", "content": user_input},
    ]
    raw_text = stream_model(messages)
    reply = parse_model_reply(raw_text, state)
    return reply, raw_text


def handle_action(reply: ModelReply, state: AgentState) -> Dict[str, Any]:
    mode = reply.action.get("mode", "none")
    if mode == "use_tool":
        tool_name = reply.action.get("tool_name")
        args = reply.action.get("tool_arguments", {})
        tool = TOOLS.get(tool_name)
        if not tool:
            return {"success": False, "message": f"Unknown tool {tool_name}", "error": ""}
        return tool(**args)
    if mode == "define_tool":
        meta = reply.action.get("new_tool")
        if meta:
            state.known_tools.append(meta)
        return {"success": True, "message": "Tool definition recorded (metadata only)", "tool_meta": meta}
    if mode == "update_prompt":
        return {
            "success": True,
            "message": "Prompt extension updated",
            "prompt_extension_update": reply.action.get("prompt_extension_update", ""),
        }
    return {"success": True, "message": "No action"}


def next_user_message(executed_step: str, remaining_plan: List[str], action_result: Dict[str, Any]) -> str:
    return (
        f"Executed step: {executed_step or 'n/a'} | success={action_result.get('success')} | "
        f"message={action_result.get('message')} | error={action_result.get('error', '')}. "
        f"Pending plan: {remaining_plan}. Continue executing the next step with available tools, "
        f"update summaries, and respond in strict JSON only."
    )


def run_agent_cycle(state: AgentState, initial_user_input: str) -> None:
    user_message = initial_user_input
    for _ in range(MAX_AUTO_STEPS):
        reply, raw_text = call_model(state, user_message)

        if reply.clarification.get("needed"):
            print("Agent asks:", reply.clarification.get("question", ""))
            break

        # Refresh plan from model reply when provided
        if reply.plan:
            state.plan_queue = reply.plan.copy()

        # Execute current step if any
        executed_step = state.plan_queue[0] if state.plan_queue else ""
        action_result = handle_action(reply, state)

        # Apply prompt extension update if present
        if reply.action.get("mode") == "update_prompt":
            ext = reply.action.get("prompt_extension_update") or ""
            if ext.strip():
                state.prompt_extension += "\n" + ext.strip()

        # Update summaries from model output
        if reply.summaries:
            state.chat_summary = reply.summaries.get("chat_summary", state.chat_summary)
            state.project_summary = reply.summaries.get("project_summary", state.project_summary)
            state.project_keywords = reply.summaries.get("project_keywords", state.project_keywords)

        # Advance plan queue after action
        if state.plan_queue:
            state.plan_queue = state.plan_queue[1:]

        state.save(STATE_PATH)

        remaining_plan = state.plan_queue
        print("\nPlan:", reply.plan)
        print("Remaining plan queue:", remaining_plan)
        print("Action:", reply.action.get("mode"), reply.action.get("tool_name", ""))
        print("Tool result:", action_result)
        print("Self-review:", reply.self_review)
        print("Summaries updated.")
        print("Raw model text length:", len(raw_text))
        print("-" * 40)

        if not remaining_plan and reply.action.get("mode") == "none":
            break

        user_message = next_user_message(executed_step, remaining_plan, action_result)
    else:
        print(f"Stopped after {MAX_AUTO_STEPS} automatic steps to avoid loops.")


def main() -> None:
    if not os.path.exists(STATE_PATH):
        print("State file missing; create agent_state.json first.", file=sys.stderr)
        sys.exit(1)

    state = AgentState.load(STATE_PATH)
    print("Self-building agent ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Bye.")
            break
        run_agent_cycle(state, user_input)


if __name__ == "__main__":
    main()
