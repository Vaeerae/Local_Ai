from __future__ import annotations
from ast import arguments
import os
import subprocess
from typing import Any, Callable, Dict

ENCODING = "utf-8-sig"


def _tool_result(success: bool, message: str, output: Any = None, error: str = "") -> Dict[str, Any]:
    return {"success": success, "message": message, "output": output, "error": error}


def create_directory(path: str) -> Dict[str, Any]:
    try:
        os.makedirs(path, exist_ok=True)
        return _tool_result(True, f"Created directory {path}")
    except Exception as exc:
        return _tool_result(False, "Failed to create directory", error=str(exc))


def write_file(path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    try:
        if os.path.exists(path) and not overwrite:
            return _tool_result(False, "File exists and overwrite is False")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding=ENCODING) as f:
            f.write(content)
        return _tool_result(True, f"Wrote file {path}", output=len(content))
    except Exception as exc:
        return _tool_result(False, "Failed to write file", error=str(exc))


def run_shell(command: str, workdir: str = ".") -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
        success = proc.returncode == 0
        return _tool_result(
            success,
            "Command executed" if success else f"Command failed ({proc.returncode})",
            output=proc.stdout.strip(),
            error=proc.stderr.strip(),
        )
    except Exception as exc:
        return _tool_result(False, "Exception during command", error=str(exc))


def append_tool_from_template(name: str, template_lines: Any) -> Dict[str, Any]:
    """Append a new tool function to this file using provided template lines."""
    try:
        if not template_lines:
            return _tool_result(False, "No template provided")
        if isinstance(template_lines, list):
            code = "\n".join(template_lines)
        else:
            code = str(template_lines)
        with open(__file__, "r", encoding=ENCODING) as f:
            content = f.read()
        if f"def {name}" in content:
            return _tool_result(True, f"Tool {name} already exists; skipped append")
        with open(__file__, "a", encoding=ENCODING) as f:
            f.write("\n\n" + code + "\n")
        return _tool_result(True, f"Appended tool {name}")
    except Exception as exc:
        return _tool_result(False, "Failed to append tool", error=str(exc))


def load_tools() -> Dict[str, Callable]:
    """Return callable tools dictionary."""
    candidates = {
        "create_directory": create_directory,
        "write_file": write_file,
        "run_shell": run_shell,
    }
    # Include any additional callables defined after import
    for name, func in list(globals().items()):
        if name.startswith("_"):
            continue
        if callable(func) and name not in candidates:
            candidates[name] = func
    return candidates


__all__ = ["create_directory", "write_file", "run_shell", "append_tool_from_template", "load_tools"]


import os

# UI-Struktur für Electron (HTML/CSS/JS) oder Tkinter (Python)
def create_ui_structure():
    if arguments.framework == 'electron':
        # Electron-Struktur (HTML/CSS/JS)
        os.makedirs(os.path.join(arguments.output_path, 'electron'), exist_ok=True)
        electron_path = os.path.join(arguments.output_path, 'electron')
        
        # Haupt-UI-Dateien
        with open(os.path.join(electron_path, 'index.html'), 'w') as f:
            f.write('''<!DOCTYPE html><html><head><title>Chat-Explorer</title><link rel="stylesheet" href="styles.css"></head><body><div class="container"><div class="explorer" id="explorer"></div><div class="chat" id="chat"></div></div><script src="app.js"></script></body></html>''')
        
        with open(os.path.join(electron_path, 'styles.css'), 'w') as f:
            f.write('''body { margin: 0; padding: 0; font-family: Arial, sans-serif; } .container { display: flex; height: 100vh; } .explorer { width: 30%; border-right: 1px solid #ccc; overflow-y: auto; } .chat { width: 70%; overflow-y: auto; }''')
        
        with open(os.path.join(electron_path, 'app.js'), 'w') as f:
            f.write('''document.addEventListener('DOMContentLoaded', () => { console.log('UI geladen'); });''')
        
        # Ordner-Explorer-Komponenten
        os.makedirs(os.path.join(electron_path, 'components'), exist_ok=True)
        with open(os.path.join(electron_path, 'components', 'explorer.js'), 'w') as f:
            f.write('''class Explorer { constructor() { this.render(); } render() { document.getElementById("explorer").innerHTML = "<h2>Ordner-Explorer</h2><div id=\"folder-tree\"></div>"; } } new Explorer();''')
        
        return f"Electron-UI-Struktur erstellt in: {os.path.abspath(electron_path)}"
    elif arguments.framework == 'tkinter':
        # Tkinter-Struktur (Python)
        os.makedirs(os.path.join(arguments.output_path, 'tkinter'), exist_ok=True)
        tkinter_path = os.path.join(arguments.output_path, 'tkinter')
        
        with open(os.path.join(tkinter_path, 'main.py'), 'w') as f:
            f.write('''import tkinter as tk
from tkinter import ttk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat-Explorer")
        self.root.geometry("1000x600")
        
        # Ordner-Explorer (links)
        self.explorer_frame = tk.Frame(root, width=300)
        self.explorer_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Chat-Interface (rechts)
        self.chat_frame = tk.Frame(root, width=700)
        self.chat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Beispiel: Baumansicht für Ordner
        self.tree = ttk.Treeview(self.explorer_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.heading("#0", text="Ordner", anchor=tk.W)
        self.tree.insert("", "0", text="C:\", open=True)
        self.tree.insert("0", "1", text="Projekte")
        
        # Chat-Bereich
        self.chat_text = tk.Text(self.chat_frame)
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        self.chat_text.insert(tk.END, "Hallo! Wähle einen Ordner aus.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()''')
        return f"Tkinter-UI-Struktur erstellt in: {os.path.abspath(tkinter_path)}"
    else:
        return "Unsupported framework."
