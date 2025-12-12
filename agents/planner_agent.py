from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import PlanContext, PlanStep, TaskContext


class PlannerInput(BaseModel):
    task: TaskContext


class PlannerAgent(Agent[PlannerInput, PlanContext]):
    def __init__(self, model_name: str) -> None:
        super().__init__("PlannerAgent", model_name)

    def run(self, data: PlannerInput) -> PlanContext:
        steps = [
            PlanStep(title="Analyse Aufgabe", summary="Verstehe Ziel und Randbedingungen."),
            PlanStep(title="Implementierung", summary="Erzeuge Code, Tools und Tests."),
            PlanStep(title="Validierung", summary="Führe pytest aus und verifiziere Ergebnisse."),
            PlanStep(title="Review & Abschluss", summary="Review, Fixes und Zusammenfassung."),
        ]
        return PlanContext(task_id=data.task.task_id, steps=steps)
