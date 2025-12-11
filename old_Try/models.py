from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Clarification(BaseModel):
    needed: bool = False
    question: str = ""


class Summaries(BaseModel):
    chat_summary: str = ""
    project_summary: str = ""
    project_keywords: List[str] = Field(default_factory=list)


class PlannerResponse(BaseModel):
    clarification: Clarification = Field(default_factory=Clarification)
    user_prompt_summary: str = ""
    plan: List[str] = Field(default_factory=list)
    plan_position: int = 0
    prompts_for_executor: List[str] = Field(default_factory=list)
    project_infos: List[str] = Field(default_factory=list)
    summaries: Summaries = Field(default_factory=Summaries)
    user_message: str = ""


class Action(BaseModel):
    tool_name: str = ""
    args: Dict[str, Any] = Field(default_factory=dict)


class NewTool(BaseModel):
    nameTool: str = ""
    beschreib: str = ""
    args: str = ""
    ergebniss: str = ""
    python_code: str = ""


class TestDef(BaseModel):
    tool_name: str = ""
    test_code: str = ""


class ExecutorResponse(BaseModel):
    picked_prompt: str = ""
    fast_infos: bool = False
    fast_tool: str = ""
    fast_args: Dict[str, Any] = Field(default_factory=dict)
    actions: List[Action] = Field(default_factory=list)
    new_tools: List[NewTool] = Field(default_factory=list)
    tests: List[TestDef] = Field(default_factory=list)
    execution_notes: str = ""
    next_prompt: str = ""


class ValidatorResponse(BaseModel):
    approved: bool = False
    reason: str = ""
    fix_prompt: str = ""
