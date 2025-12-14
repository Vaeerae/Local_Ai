from __future__ import annotations

"""
Lightweight Ollama client wrapper to enforce JSON responses.
"""

import json
import re
from typing import Any, Dict, Optional

try:
    import ollama
except ImportError as exc:  # pragma: no cover - optional dependency
    raise RuntimeError("ollama package is required for LLM integration.") from exc


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", timeout: int = 60) -> None:
        self.client = ollama.Client(host=host, timeout=timeout)

    def _emit_chunks(self, text: str, chunk_callback: Optional[callable]) -> str:
        """
        Split thinking blocks (<think>...</think>) from normal text and emit via callback.
        Returns the cleaned text (without thinking tags).
        """
        if not chunk_callback or not text:
            return text

        cleaned_parts = []
        pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        last_end = 0
        for match in pattern.finditer(text):
            # preceding normal text
            if match.start() > last_end:
                normal = text[last_end:match.start()]
                if normal.strip():
                    chunk_callback(normal)
                    cleaned_parts.append(normal)
            thinking = match.group(1)
            if thinking.strip():
                chunk_callback(f"[thinking] {thinking}")
            last_end = match.end()
        # tail
        if last_end < len(text):
            tail = text[last_end:]
            if tail.strip():
                chunk_callback(tail)
                cleaned_parts.append(tail)
        return "".join(cleaned_parts)

    def generate_json(
        self, model: str, prompt: str, chunk_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Request a JSON response. If parsing fails, raise a ValueError so callers can fallback.
        """
        text = ""
        options = {"temperature": 0}
        if "think" in model.lower():
            options["thinking"] = True

        if chunk_callback:
            stream = self.client.generate(
                model=model,
                prompt=prompt,
                options=options,
                stream=True,
            )
            for part in stream:
                chunk = part.get("response", "") or ""
                cleaned = self._emit_chunks(chunk, chunk_callback) if chunk else ""
                text += cleaned
                if chunk_callback and chunk and cleaned == chunk:
                    # no think tags; emit raw chunk
                    chunk_callback(chunk)
        else:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options=options,
            )
            raw = response.get("response", "") or ""
            text = self._emit_chunks(raw, chunk_callback) if chunk_callback else raw
            if chunk_callback and text == raw and raw:
                chunk_callback(raw)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama response is not valid JSON: {exc}") from exc

    def list_models(self) -> Dict[str, Any]:
        return self.client.list()
