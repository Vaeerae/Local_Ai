"""Agent base class and shared utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class Agent(ABC, Generic[InputModel, OutputModel]):
    name: str
    model_name: str

    def __init__(self, name: str, model_name: str) -> None:
        self.name = name
        self.model_name = model_name

    @abstractmethod
    def run(self, data: InputModel) -> OutputModel:
        """Execute agent logic deterministically and return validated JSON."""

