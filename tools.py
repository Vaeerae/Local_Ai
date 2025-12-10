import os
from typing import List, Dict, Any

ENCODING = "utf-8"


def generate_markdown_installation_guide(application_name: str, steps: List[str], details: List[str]) -> Dict[str, Any]:
    """Erzeugt eine Markdown-Installationsanleitung aus Schritten und Detailtexten."""
    try:
        lines = [f"# Installation und Konfiguration von {application_name}", ""]
        for step, detail in zip(steps, details):
            lines.append(f"## {step}")
            lines.append(detail)
            lines.append("")
        content = "\n".join(lines)
        return {"success": True, "content": content}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def generate_file(file_name: str, content: str) -> Dict[str, Any]:
    """Erstellt eine Datei mit angegebenem Inhalt."""
    try:
        folder = os.path.dirname(file_name)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(file_name, "w", encoding=ENCODING) as f:
            f.write(content)
        return {"success": True, "content_length": len(content)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def append_funktion_in_file(file_name: str, content: str) -> Dict[str, Any]:
    """Hängt Inhalt an eine bestehende Python-Datei an."""
    try:
        if not os.path.exists(file_name):
            return {"success": False, "error": "file not found"}
        with open(file_name, "a", encoding=ENCODING) as f:
            if content and not content.startswith("\n"):
                f.write("\n")
            f.write(content)
        return {"success": True, "appended_length": len(content)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def read_files(file_name: str) -> Dict[str, Any]:
    """Liest eine Datei und gibt ihren Inhalt zurück."""
    try:
        with open(file_name, "r", encoding=ENCODING) as f:
            data = f.read()
        return {"success": True, "content": data}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


TOOL_REGISTRY = {
    "generate_markdown_installation_guide": generate_markdown_installation_guide,
    "generate_file": generate_file,
    "append_funktion_in_file": append_funktion_in_file,
    "read_files": read_files,
}
