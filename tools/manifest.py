"""Tool manifest definitions."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class ToolManifest(BaseModel):
    name: str
    version: str
    entrypoint: str
    input_schema: Dict[str, object] = Field(default_factory=dict)
    output_schema: Dict[str, object] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
