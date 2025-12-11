from pathlib import Path
from typing import List
import sys
import ollama

from config import DEFAULT_MODEL
from io_utils import load_text


def _load_system_prompt(system_prompt: str | Path) -> str:
    try:
        path = Path(system_prompt)
        if path.exists():
            return load_text(path)
    except Exception:
        pass
    return str(system_prompt)


def call_model_streaming(system_prompt: str | Path, user_content: str, model: str = DEFAULT_MODEL) -> str:
    """
    Wrapper fuer ollama.chat mit Streaming und defensiver Fehlerbehandlung.
    Gibt den gesamten vom Modell generierten Text zurueck.
    """
    sys_prompt_text = _load_system_prompt(system_prompt)

    print(f"\n[Model {model}] Starte Streaming-Antwort")
    messages = [
        {"role": "system", "content": sys_prompt_text},
        {"role": "user", "content": user_content},
    ]

    full_content_parts: List[str] = []

    try:
        for chunk in ollama.chat(model=model, messages=messages, tools=[], stream=True):
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                full_content_parts.append(piece)
                print(piece, end="", flush=True)
    except Exception as exc:
        print(f"\n[WARN] Streaming-Fehler: {exc}", file=sys.stderr)

    print()
    return "".join(full_content_parts).strip()
