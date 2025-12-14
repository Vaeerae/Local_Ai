from __future__ import annotations

"""
Lightweight Ollama client wrapper to enforce JSON responses.
"""

import json
from typing import Any, Dict, Optional

try:
    import ollama
except ImportError as exc:  # pragma: no cover - optional dependency
    raise RuntimeError("ollama package is required for LLM integration.") from exc


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", timeout: int = 60) -> None:
        self.client = ollama.Client(host=host, timeout=timeout)

    def generate_json(
        self, model: str, prompt: str, chunk_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Request a JSON response. If parsing fails, raise a ValueError so callers can fallback.
        """
        text = ""
        if chunk_callback:
            stream = self.client.generate(
                model=model,
                prompt=prompt,
                options={"temperature": 0},
                stream=True,
            )
            for part in stream:
                chunk = part.get("response", "")
                if chunk:
                    text += chunk
                    try:
                        chunk_callback(chunk)
                    except Exception:
                        pass
        else:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options={"temperature": 0},
            )
            text = response.get("response", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama response is not valid JSON: {exc}") from exc

    def list_models(self) -> Dict[str, Any]:
        return self.client.list()
