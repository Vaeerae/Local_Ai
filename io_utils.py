from pathlib import Path
from typing import Any
import json

from config import ENCODING


def safe_open(path: str | Path, mode: str = "r"):
    return open(path, mode, encoding=ENCODING)


def load_text(path: str | Path) -> str:
    with safe_open(path, "r") as f:
        return f.read()


def dump_json(path: str | Path, data: Any) -> None:
    with safe_open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
