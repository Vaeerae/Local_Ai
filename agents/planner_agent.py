from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import PlanContext, PlanStep, TaskContext
from prompts import build_prompt


class PlannerInput(BaseModel):
    task: TaskContext


class PlannerAgent(Agent[PlannerInput, PlanContext]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("PlannerAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

    def run(self, data: PlannerInput) -> PlanContext:
        steps = [
            PlanStep(title="Analyse Aufgabe", summary="Verstehe Ziel und Randbedingungen."),
            PlanStep(title="Implementierung", summary="Erzeuge Code, Tools und Tests."),
            PlanStep(title="Validierung", summary="Führe pytest aus und verifiziere Ergebnisse."),
            PlanStep(title="Review & Abschluss", summary="Review, Fixes und Zusammenfassung."),
        ]
        version = "0.1.0"
        if self.llm_client:
            user_prompt = (
                "Erstelle einen Plan als JSON für die Aufgabe:\n"
                f"\"{data.task.description}\"\n"
                "Antwortformat:\n"
                '{ "version": "0.1.0", "steps": [ { "title": "", "summary": "" } ] }\n'
            )
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt("planner", user_prompt, language=data.task.language),
                    chunk_callback=self._stream_chunk,
                )
                raw_steps = resp.get("steps", [])
                steps = [
                    PlanStep(title=s.get("title", ""), summary=s.get("summary", ""))
                    for s in raw_steps
                    if s.get("title")
                ] or steps
                version = resp.get("version", version)
            except Exception:
                pass
        return PlanContext(task_id=data.task.task_id, steps=steps, version=version)
