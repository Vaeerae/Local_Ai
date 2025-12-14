from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Tuple


def write_context_log(base_dir: Path, filename: str, sections: List[Tuple[str, str]]) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
    path = base_dir / f"{ts}_{filename}.txt"
    lines = []
    for idx, (title, content) in enumerate(sections, start=1):
        lines.append(f"{idx}. {title}")
        lines.append(content)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
