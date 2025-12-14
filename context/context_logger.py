from __future__ import annotations

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


def _next_run_dir(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted([p for p in base_dir.glob("run_*") if p.is_dir()])
    next_idx = len(existing) + 1
    run_dir = base_dir / f"run_{next_idx:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _next_context_index(run_dir: Path) -> int:
    existing = sorted(run_dir.glob("context_*.txt"))
    return len(existing) + 1


def start_run(base_dir: Path) -> Path:
    return _next_run_dir(base_dir)


def write_raw_context(run_dir: Path, stage: str, raw: str) -> Path:
    """
    Write raw context exactly as passed to the model, preceded by a single header line.
    """
    idx = _next_context_index(run_dir)
    path = run_dir / f"context_{idx:03d}.txt"
    path.write_text(f"{stage}\n{raw}", encoding="utf-8")
    return path
