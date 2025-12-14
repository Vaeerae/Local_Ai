from __future__ import annotations

from pydantic import BaseModel

from agents.base import Agent
from context.models import ResearchFinding
from prompts import build_prompt


class ResearchInput(BaseModel):
    task_description: str
    step_summary: str
    plan_titles: list[str]
    language: str
    prior_findings: list[ResearchFinding] = []


class ResearchOutput(BaseModel):
    findings: list[ResearchFinding]


class ResearchAgent(Agent[ResearchInput, ResearchOutput]):
    def __init__(self, model_name: str, llm_client=None, stream_callback=None) -> None:
        super().__init__("ResearchAgent", model_name, llm_client=llm_client, stream_callback=stream_callback)

    def run(self, data: ResearchInput) -> ResearchOutput:
        findings: list[ResearchFinding] = list(data.prior_findings)
        if self.llm_client:
            user_prompt = (
                "Sammle fehlende Informationen für den aktuellen Schritt.\n"
                f"Aufgabe: {data.task_description}\n"
                f"Aktueller Schritt: {data.step_summary}\n"
                f"Plan-Titel: {data.plan_titles}\n"
                "Gib JSON zurück im Schema: {\"findings\": [{\"source\": \"string\", \"content\": \"string\"}]}\n"
                "Wenn keine neuen Infos: gib leere Liste."
            )
            try:
                resp = self.llm_client.generate_json(
                    self.model_name,
                    build_prompt("research", user_prompt, language=data.language),
                    chunk_callback=self._stream_chunk,
                )
                raw_findings = resp.get("findings", [])
                findings = [
                    ResearchFinding(source=f.get("source", "unknown"), content=f.get("content", ""))
                    for f in raw_findings
                    if f.get("content")
                ]
            except Exception:
                pass
        return ResearchOutput(findings=findings)
