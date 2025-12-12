"""
Tool registry for managing manifest lifecycle.

New tools are validated before being added to the registry to avoid unsafe
permissions or malformed manifests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from pydantic import ValidationError

from tools.manifest import ToolManifest


class ToolRegistry:
    def __init__(self, root: Path, allowed_permissions: Optional[list[str]] = None):
        self.root = root
        self.allowed_permissions = set(allowed_permissions or [])
        self._manifests: Dict[str, ToolManifest] = {}
        self.root.mkdir(parents=True, exist_ok=True)
        self._load_existing()

    @property
    def manifests(self) -> Dict[str, ToolManifest]:
        return self._manifests

    def _load_existing(self) -> None:
        for manifest_file in self.root.glob("*/manifest.json"):
            try:
                manifest = ToolManifest.model_validate_json(manifest_file.read_text())
                self._manifests[manifest.name] = manifest
            except ValidationError:
                continue

    def register(self, manifest: ToolManifest) -> None:
        self._validate_permissions(manifest)
        tool_dir = self.root / manifest.name
        tool_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = tool_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))
        self._manifests[manifest.name] = manifest

    def get(self, name: str) -> Optional[ToolManifest]:
        return self._manifests.get(name)

    def _validate_permissions(self, manifest: ToolManifest) -> None:
        unauthorized = set(manifest.permissions) - self.allowed_permissions
        if unauthorized:
            raise ValueError(f"Unauthorized tool permissions: {unauthorized}")

    def to_json(self) -> str:
        return json.dumps(
            {name: manifest.model_dump() for name, manifest in self._manifests.items()},
            indent=2,
        )
