from __future__ import annotations

import json
from typing import Callable, Dict, List, Optional

from agents.decomposer_agent import DecomposerAgent, DecomposerInput
from agents.executor_agent import ExecutorAgent, ExecutorInput
from agents.fix_manager_agent import FixManagerAgent, FixManagerInput
from agents.intake_agent import IntakeAgent, IntakeInput
from agents.planner_agent import PlannerAgent, PlannerInput
from agents.prompter_agent import PrompterAgent, PrompterInput
from agents.reviewer_agent import ReviewerAgent, ReviewerInput
from agents.research_agent import ResearchAgent, ResearchInput
from agents.summarizer_agent import SummarizerAgent, SummarizerInput
from config.config import AppConfig, resolve_paths
from context.models import (
    ExecutionContext,
    ExecutionRequest,
    PlanContext,
    PromptContext,
    ProjectMemory,
    ResearchFinding,
    ReviewContext,
    ReviewDecision,
    StepContext,
    TaskContext,
)
from llm.ollama_client import OllamaClient
from orchestrator.events import EventRecord, EventType
from orchestrator.state import OrchestratorState, StateTracker
from runner.pytest_runner import PytestRunner
from storage.event_store import EventStore
from storage.snapshots import SnapshotWriter
from tools.registry import ToolRegistry


ProgressCallback = Callable[[str, Dict[str, object]], None]


class Orchestrator:
    def __init__(
        self,
        config: AppConfig,
        llm_client: OllamaClient | None = None,
        on_event: Optional[ProgressCallback] = None,
        on_stream: Optional[ProgressCallback] = None,
    ) -> None:
        self.config = resolve_paths(config)
        self.state = StateTracker(max_fixes=5)
        self.event_store = EventStore(self.config.storage_dir / "events.db")
        self.snapshot_writer = SnapshotWriter(self.config.context_snapshot_dir)
        self.tool_registry = ToolRegistry(
            root=self.config.tool_dir, allowed_permissions=self.config.allowed_tool_permissions
        )
        self.runner = PytestRunner(
            workspace=self.config.runner_workspace, timeout_seconds=self.config.pytest_timeout_seconds
        )
        models = self.config.as_agent_config()
        self.llm_client = llm_client or OllamaClient(
            host=self.config.ollama_host, timeout=self.config.ollama_timeout
        )
        self.on_event = on_event
        self.on_stream = on_stream
        self.intake_agent = IntakeAgent(
            models["intake"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.planner_agent = PlannerAgent(
            models["planner"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.decomposer_agent = DecomposerAgent(
            models["decomposer"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.prompter_agent = PrompterAgent(
            models["prompter"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.executor_agent = ExecutorAgent(
            models["executor"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.reviewer_agent = ReviewerAgent(
            models["reviewer"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.fix_manager_agent = FixManagerAgent(
            models["fix_manager"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.summarizer_agent = SummarizerAgent(
            models["summarizer"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.research_agent = ResearchAgent(
            models["research"], llm_client=self.llm_client, stream_callback=self.on_stream
        )
        self.memory = ProjectMemory()

    def set_stream_callback(self, cb: Optional[ProgressCallback]) -> None:
        self.on_stream = cb
        for agent in (
            self.intake_agent,
            self.planner_agent,
            self.decomposer_agent,
            self.research_agent,
            self.prompter_agent,
            self.executor_agent,
            self.reviewer_agent,
            self.fix_manager_agent,
            self.summarizer_agent,
        ):
            agent.stream_callback = cb

    def run(self, task_description: str) -> Dict[str, object]:
        task_ctx = self._intake(task_description)
        plan_ctx = self._plan(task_ctx)
        reviews: List[ReviewContext] = []

        for idx, step in enumerate(plan_ctx.steps):
            self.state.active_step_id = step.step_id
            step_ctx = self._decompose(plan_ctx, idx)
            research = self._research(task_ctx, plan_ctx, step_ctx)
            prompt_ctx = self._prompt(task_ctx, step_ctx, plan_ctx, research)
            exec_request = self._execute(step_ctx, prompt_ctx, research)
            execution_ctx = self._run_code(step_ctx, plan_ctx, prompt_ctx, exec_request, research)
            review_ctx = self._review(execution_ctx)

            if review_ctx.decision != ReviewDecision.APPROVED:
                review_ctx = self._fix_loop(execution_ctx, review_ctx)

            reviews.append(review_ctx)
            plan_ctx.current_step_index = idx + 1
            self.state.reset_fix()

        summary = self._summarize(task_ctx, plan_ctx, reviews)
        self._log_event(EventType.RUN_COMPLETED, {"task_id": task_ctx.task_id})
        return {
            "task": task_ctx.model_dump(),
            "plan": plan_ctx.model_dump(),
            "reviews": [r.model_dump() for r in reviews],
            "summary": summary,
        }

    def _intake(self, description: str) -> TaskContext:
        self.state.next(OrchestratorState.INTAKE)
        result = self.intake_agent.run(IntakeInput(description=description, language=self.config.language))
        self._log_event(EventType.TASK_CREATED, result.model_dump())
        self.snapshot_writer.write("task", result.model_dump())
        return result

    def _plan(self, task: TaskContext) -> PlanContext:
        self.state.next(OrchestratorState.PLAN)
        result = self.planner_agent.run(PlannerInput(task=task))
        self._log_event(EventType.PLAN_CREATED, result.model_dump())
        self.snapshot_writer.write("plan", result.model_dump())
        return result

    def _decompose(self, plan: PlanContext, step_index: int) -> StepContext:
        self.state.next(OrchestratorState.DECOMPOSE)
        return self.decomposer_agent.run(DecomposerInput(plan=plan, step_index=step_index))

    def _research(self, task: TaskContext, plan: PlanContext, step: StepContext) -> List[ResearchFinding]:
        self.state.next(OrchestratorState.RESEARCH)
        output = self.research_agent.run(
            ResearchInput(
                task_description=task.description,
                step_summary=step.summary,
                plan_titles=[s.title for s in plan.steps],
                language=task.language,
                prior_findings=[],
            )
        )
        return output.findings

    def _prompt(self, task: TaskContext, step: StepContext, plan: PlanContext, findings: List[ResearchFinding]) -> PromptContext:
        self.state.next(OrchestratorState.PROMPT_BUILD)
        prompt = self.prompter_agent.run(
            PrompterInput(task=task, step=step, plan=plan, findings=findings)
        )
        return prompt

    def _execute(self, step: StepContext, prompt: PromptContext, findings: List[ResearchFinding]) -> ExecutionRequest:
        self.state.next(OrchestratorState.EXECUTE)
        exec_request = self.executor_agent.run(
            ExecutorInput(step=step, prompt=prompt, findings=findings)
        )
        return exec_request

    def _run_code(
        self,
        step: StepContext,
        plan: PlanContext,
        prompt: PromptContext,
        request: ExecutionRequest,
        findings: List[ResearchFinding],
    ) -> ExecutionContext:
        self.state.next(OrchestratorState.RUN_CODE)
        result = self.runner.run(request)
        context = ExecutionContext(
            step_id=step.step_id,
            plan_id=plan.plan_id,
            task_id=plan.task_id,
            prompt=prompt,
            request=request,
            result=result,
            research_findings=findings,
        )
        payload = {
            "step_id": step.step_id,
            "status": result.status.value,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        event_type = EventType.STEP_EXECUTED if result.status.value == "PASSED" else EventType.TEST_FAILED
        self._log_event(event_type, payload)
        self.snapshot_writer.write("execution", context.model_dump())
        return context

    def _review(self, execution: ExecutionContext) -> ReviewContext:
        self.state.next(OrchestratorState.REVIEW)
        return self.reviewer_agent.run(ReviewerInput(execution=execution))

    def _fix_loop(self, execution: ExecutionContext, review: ReviewContext) -> ReviewContext:
        self.state.next(OrchestratorState.FIX)
        while self.state.fix_attempts < self.state.max_fixes and review.decision != ReviewDecision.APPROVED:
            self.state.increment_fix()
            fix_instr = self.fix_manager_agent.run(FixManagerInput(review=review, execution=execution))
            # For now we do not auto-apply fixes; they are recorded and the loop stops.
            self._log_event(
                EventType.ERROR_ABORTED,
                {
                    "step_id": execution.step_id,
                    "reason": "Auto-fix not applied",
                    "attempt": self.state.fix_attempts,
                    "fix": fix_instr.model_dump(),
                },
            )
            break
        return review

    def _summarize(
        self, task: TaskContext, plan: PlanContext, reviews: List[ReviewContext]
    ) -> Dict[str, object]:
        self.state.next(OrchestratorState.SUMMARIZE)
        summary = self.summarizer_agent.run(
            SummarizerInput(task=task, plan=plan, reviews=reviews, memory=self.memory)
        )
        self.memory = summary.memory
        self.snapshot_writer.write("summary", summary.model_dump())
        return summary.model_dump()

    def _log_event(self, event_type: EventType, payload: Dict[str, object]) -> None:
        event = EventRecord(event_type=event_type, payload=payload)
        self.event_store.append(event)
        if self.on_event:
            try:
                self.on_event(event_type.value, payload)
            except Exception:
                pass
