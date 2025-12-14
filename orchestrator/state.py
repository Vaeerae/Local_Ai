"""Orchestrator state machine enums and helpers."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class OrchestratorState(str, Enum):
    INTAKE = "INTAKE"
    PLAN = "PLAN"
    STEP_LOOP = "STEP_LOOP"
    DECOMPOSE = "DECOMPOSE"
    RESEARCH = "RESEARCH"
    PROMPT_BUILD = "PROMPT_BUILD"
    EXECUTE = "EXECUTE"
    RUN_CODE = "RUN_CODE"
    REVIEW = "REVIEW"
    FIX = "FIX"
    SUMMARIZE = "SUMMARIZE"
    FINALIZE = "FINALIZE"


class StateTracker:
    """Tracks current state and fix-attempt budget."""

    def __init__(self, max_fixes: int = 5) -> None:
        self.current: OrchestratorState = OrchestratorState.INTAKE
        self.fix_attempts: int = 0
        self.max_fixes = max_fixes
        self.active_step_id: Optional[str] = None

    def next(self, state: OrchestratorState) -> OrchestratorState:
        self.current = state
        return state

    def increment_fix(self) -> None:
        self.fix_attempts += 1

    def reset_fix(self) -> None:
        self.fix_attempts = 0
