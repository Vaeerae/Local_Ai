import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

import ollama
from pydantic import BaseModel, Field, ValidationError

STATE_PATH = os.path.join(os.path.dirname(__file__), "agent_state.json")
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "base_system_prompt.txt")
DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "ministral-3:14b")


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@dataclass
class AgentState:
    chat_summary: str
    project_summary: str
    project_keywords: List[str]
    prompt_extension: str

    @staticmethod
    def load(path: str) -> "AgentState":
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return AgentState(
            chat_summary=data.get("chat_summary", ""),
            project_summary=data.get("project_summary", ""),
            project_keywords=data.get("project_keywords", []),
            prompt_extension=data.get("prompt_extension", ""),
        )

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8-sig") as f:
            json.dump(asdict(self), f, indent=2)


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
        with open(path, "w", encoding="utf-8") as f:
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
    return base


def call_model(state: AgentState, user_input: str) -> ModelReply:
    system_prompt = build_system_prompt(state)
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"Chat summary: {state.chat_summary}\nProject summary: {state.project_summary}\nKeywords: {', '.join(state.project_keywords)}",
        },
        {"role": "user", "content": user_input},
    ]
    resp = ollama.chat(model=DEFAULT_MODEL, messages=messages)
    content = resp["message"]["content"]
    try:
        data = json.loads(content)
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


def handle_action(reply: ModelReply) -> Dict[str, Any]:
    mode = reply.action.get("mode", "none")
    if mode == "use_tool":
        tool_name = reply.action.get("tool_name")
        args = reply.action.get("tool_arguments", {})
        tool = TOOLS.get(tool_name)
        if not tool:
            return {"success": False, "message": f"Unknown tool {tool_name}", "error": ""}
        return tool(**args)
    elif mode == "define_tool":
        return {"success": True, "message": "Tool definition recorded (metadata only)", "tool_meta": reply.action.get("new_tool")}
    elif mode == "update_prompt":
        return {"success": True, "message": "Prompt extension updated", "prompt_extension_update": reply.action.get("prompt_extension_update", "")}
    return {"success": True, "message": "No action"}


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

        reply = call_model(state, user_input)

        if reply.clarification.get("needed"):
            print("Agent asks:", reply.clarification.get("question", ""))
            continue

        action_result = handle_action(reply)

        # Apply prompt extension update if present
        if reply.action.get("mode") == "update_prompt":
            state.prompt_extension += "\n" + (reply.action.get("prompt_extension_update") or "")

        # Update summaries from model output
        if reply.summaries:
            state.chat_summary = reply.summaries.get("chat_summary", state.chat_summary)
            state.project_summary = reply.summaries.get("project_summary", state.project_summary)
            state.project_keywords = reply.summaries.get("project_keywords", state.project_keywords)

        state.save(STATE_PATH)

        # Show concise feedback to the user
        print("\nPlan:", reply.plan)
        print("Action:", reply.action.get("mode"), reply.action.get("tool_name", ""))
        print("Tool result:", action_result)
        print("Self-review:", reply.self_review)
        print("Summaries updated.")
        print("-" * 40)


if __name__ == "__main__":
    main()
