"""Agent base class and shared utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, Optional, TypeVar

from pydantic import BaseModel

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)
StreamCallback = Callable[[str, str], None]


class Agent(ABC, Generic[InputModel, OutputModel]):
    name: str
    model_name: str
    llm_client: Optional[object]
    stream_callback: Optional[StreamCallback]

    def __init__(
        self,
        name: str,
        model_name: str,
        llm_client: Optional[object] = None,
        stream_callback: Optional[StreamCallback] = None,
    ) -> None:
        self.name = name
        self.model_name = model_name
        self.llm_client = llm_client
        self.stream_callback = stream_callback

    @abstractmethod
    def run(self, data: InputModel) -> OutputModel:
        """Execute agent logic deterministically and return validated JSON."""

    def _stream_chunk(self, chunk: str) -> None:
        if self.stream_callback:
            try:
                self.stream_callback(self.name, chunk)
            except Exception:
                pass
