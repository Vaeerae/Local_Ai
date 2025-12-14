"""
Simple websearch tool using urllib (GET). Returns raw text snippet.
"""

from __future__ import annotations

import urllib.request
from typing import Dict


def run(query: str, limit: int = 1024) -> Dict[str, str]:
    """
    Perform a simple GET request to the given URL (query treated as URL).
    Returns a dict with 'url' and 'content' (truncated).
    """
    with urllib.request.urlopen(query, timeout=15) as resp:
        data = resp.read(limit * 4)
    text = data.decode("utf-8", errors="ignore")
    return {"url": query, "content": text[:limit]}
