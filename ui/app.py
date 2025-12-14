from __future__ import annotations

"""
Minimal PySide6 UI shell with chat-style pane and settings popup.

The UI loads lazily to avoid import errors when PySide6 is not installed. A
RuntimeError is raised with guidance instead of failing on import.
"""

from pathlib import Path
from typing import List, Optional
import threading
import queue


def run_ui(
    app_title: str,
    status_text: str = "Idle",
    workspace_path: Optional[Path] = None,
    task_description: str | None = None,
    plan_steps: Optional[List[str]] = None,
    language: str = "de",
    models: Optional[dict] = None,
    orchestrator: Optional[object] = None,
) -> None:
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QFileSystemModel,
            QComboBox,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QPushButton,
            QSplitter,
            QDialog,
            QDialogButtonBox,
            QTextBrowser,
            QTextEdit,
            QTreeView,
            QVBoxLayout,
            QWidget,
        )
        from PySide6.QtCore import Qt, QTimer
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("PySide6 is required for the UI but is not installed.") from exc

    def _list_ollama_models() -> List[str]:
        try:
            import ollama

            client = ollama.Client()
            result = client.list()
            return [m["model"] for m in result.get("models", [])]
        except Exception:
            return []

    class SettingsDialog(QDialog):
        def __init__(
            self,
            parent,
            current_language: str,
            current_models: dict,
            available_models: List[str],
            use_unified_model: bool = False,
            unified_model_value: str = "",
        ):
            super().__init__(parent)
            self.setWindowTitle("Einstellungen")
            self.lang_combo = QComboBox()
            self.lang_combo.addItems(["de", "en"])
            self.lang_combo.setCurrentText(current_language or "de")

            self.model_inputs = {}
            form = QFormLayout()
            form.addRow("Sprache", self.lang_combo)

            self.available_models = available_models or []
            self.model_selector = QComboBox()
            if self.available_models:
                self.model_selector.addItems(self.available_models)

            self.unified_toggle = QComboBox()
            self.unified_toggle.addItems(["pro Agent", "ein Modell für alle"])
            self.unified_toggle.setCurrentText("ein Modell für alle" if use_unified_model else "pro Agent")
            form.addRow("Modellmodus", self.unified_toggle)

            self.unified_model = QComboBox()
            if self.available_models:
                self.unified_model.addItems(self.available_models)
            if unified_model_value and unified_model_value in self.available_models:
                self.unified_model.setCurrentText(unified_model_value)
            self.unified_model_row = (QLabel("Gemeinsames Modell"), self.unified_model)
            form.addRow(*self.unified_model_row)

            self.per_agent_rows = []
            models_map = current_models or {}
            for agent_name, model_name in sorted(models_map.items()):
                combo = QComboBox()
                entries = self.available_models or [model_name]
                combo.addItems(entries)
                if model_name in entries:
                    combo.setCurrentText(model_name)
                self.model_inputs[agent_name] = combo
                label = QLabel(f"Modell {agent_name}")
                self.per_agent_rows.append((label, combo))
                form.addRow(label, combo)

            self._sync_visibility(use_unified_model)
            self.unified_toggle.currentTextChanged.connect(
                lambda _: self._sync_visibility(self.unified_toggle.currentText() == "ein Modell für alle")
            )

            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)

            layout = QVBoxLayout(self)
            layout.addLayout(form)
            layout.addWidget(buttons)

        def get_values(self) -> tuple[str, dict]:
            models = {k: v.currentText() for k, v in self.model_inputs.items()}
            use_unified = self.unified_toggle.currentText() == "ein Modell für alle"
            unified_model = self.unified_model.currentText() if use_unified else ""
            return self.lang_combo.currentText(), models, use_unified, unified_model

        def _sync_visibility(self, use_unified: bool) -> None:
            # Show only unified model field if unified mode; hide per-agent rows
            self.unified_model_row[0].setVisible(use_unified)
            self.unified_model_row[1].setVisible(use_unified)
            for label, combo in self.per_agent_rows:
                label.setVisible(not use_unified)
                combo.setVisible(not use_unified)

    class MainWindow(QMainWindow):
        def __init__(
            self,
            title: str,
            status: str,
            workspace: Optional[Path],
            task: Optional[str],
            steps: Optional[List[str]],
            language: str,
            models: Optional[dict],
        ) -> None:
            super().__init__()
            self.setWindowTitle(title)
            self.resize(1200, 800)
            self.language = language or "de"
            self.models = models or {}
            self.available_models = _list_ollama_models()
            self.orchestrator = orchestrator
            self._run_queue: queue.Queue = queue.Queue()
            self._worker_thread: Optional[threading.Thread] = None
            self._event_queue: queue.Queue = queue.Queue()
            self._stream_queue: queue.Queue = queue.Queue()
            self.chat_entries: list[dict] = []
            self.stream_buffers: dict[str, dict] = {}
            if self.orchestrator is not None:
                try:
                    self.orchestrator.on_event = self._enqueue_event
                    if hasattr(self.orchestrator, "set_stream_callback"):
                        self.orchestrator.set_stream_callback(self._on_stream_chunk)
                except Exception:
                    pass

            # Left: workspace tree
            left = QTreeView()
            model = QFileSystemModel(left)
            root = str(workspace or Path.cwd())
            model.setRootPath(root)
            left.setModel(model)
            left.setRootIndex(model.index(root))
            left.setColumnWidth(0, 300)

            # Right: chat area with header
            header_layout = QHBoxLayout()
            status_label = QLabel(status)
            settings_button = QPushButton("⋯")
            settings_button.setFixedWidth(32)
            settings_button.clicked.connect(self._open_settings)
            header_layout.addWidget(status_label)
            header_layout.addStretch()
            header_layout.addWidget(settings_button)

            from PySide6.QtGui import QTextCursor

            self.chat_view = QTextBrowser()
            self.chat_view.setOpenLinks(False)
            self.chat_view.anchorClicked.connect(self._handle_anchor)
            self.chat_input = QLineEdit()
            send_button = QPushButton("Senden")
            send_button.clicked.connect(self._send_message)
            self.chat_input.returnPressed.connect(self._send_message)

            chat_layout = QVBoxLayout()
            chat_layout.addLayout(header_layout)
            chat_layout.addWidget(self.chat_view, stretch=5)

            input_row = QHBoxLayout()
            input_row.addWidget(self.chat_input, stretch=4)
            input_row.addWidget(send_button, stretch=1)
            chat_layout.addLayout(input_row)

            chat_widget = QWidget()
            chat_widget.setLayout(chat_layout)

            # Splitter layout
            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(left)
            splitter.addWidget(chat_widget)
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 3)

            # Status bar substitute
            bottom = QLabel(status)
            bottom.setObjectName("statusLabel")

            container = QWidget()
            root_layout = QVBoxLayout(container)
            root_layout.addWidget(splitter)
            root_layout.addWidget(bottom)
            root_layout.setStretch(0, 10)
            root_layout.setStretch(1, 1)

            self.setCentralWidget(container)

            # Initial context messages
            if task:
                self._append_chat("System", f"Aufgabe: {task}")
            if steps:
                self._append_chat("System", f"Plan: {steps}")

        def _open_settings(self) -> None:
            dlg = SettingsDialog(
                self,
                self.language,
                self.models,
                self.available_models,
                use_unified_model=getattr(self.orchestrator.config, "unified_model", False)
                if self.orchestrator else False,
                unified_model_value=getattr(self.orchestrator.config, "unified_model_name", "")
                if self.orchestrator else "",
            )
            if dlg.exec():
                lang, models, use_unified, unified_model = dlg.get_values()
                self.language = lang
                if use_unified and unified_model:
                    # apply one model to all agents
                    self.models = {k: unified_model for k in models.keys() or self.models.keys()}
                    if self.orchestrator:
                        try:
                            self.orchestrator.config.unified_model = True
                            self.orchestrator.config.unified_model_name = unified_model
                            for agent_name in (
                                "planner",
                                "research",
                                "decomposer",
                                "prompter",
                                "executor",
                                "reviewer",
                                "fix_manager",
                                "summarizer",
                            ):
                                attr = f"{agent_name}_agent"
                                if hasattr(self.orchestrator, attr):
                                    getattr(self.orchestrator, attr).model_name = unified_model
                        except Exception:
                            pass
                else:
                    self.models.update(models)
                    if self.orchestrator:
                        try:
                            self.orchestrator.config.unified_model = False
                            self.orchestrator.config.language = lang
                            for agent_key, model_name in models.items():
                                attr = f"{agent_key}_agent"
                                if hasattr(self.orchestrator, attr):
                                    getattr(self.orchestrator, attr).model_name = model_name
                        except Exception:
                            pass

        def _append_chat(self, sender: str, message: str, loading: bool = False) -> None:
            self.chat_entries.append(
                {"type": "msg", "role": sender, "text": message, "loading": loading}
            )
            self._render_chat()

        def _append_chat_only_user(self, message: str) -> None:
            self.chat_entries.append({"type": "msg", "role": "User", "text": message, "loading": False})
            self._render_chat()

        def _enqueue_event(self, event_type: str, payload: dict) -> None:
            self._event_queue.put((event_type, payload))

        def _handle_anchor(self, url) -> None:
            target = url.toString()
            if target.startswith("toggle:"):
                source = target.split("toggle:", 1)[1]
                if source in self.stream_buffers:
                    self.stream_buffers[source]["open"] = not self.stream_buffers[source]["open"]
                    self._render_chat()

        def _ensure_stream_entry(self, source: str) -> None:
            if source not in self.stream_buffers:
                self.stream_buffers[source] = {"open": False, "text": ""}
                self.chat_entries.append({"type": "stream", "source": source})

        def _on_stream_chunk(self, source: str, chunk: str) -> None:
            # Called from worker thread -> enqueue to main thread
            self._stream_queue.put((source, chunk))

        def _render_chat(self) -> None:
            import html

            rendered = []
            for entry in self.chat_entries:
                etype = entry.get("type")
                if etype == "stream":
                    source = entry["source"]
                    buf = self.stream_buffers.get(source, {"text": "", "open": False})
                    arrow = "▼" if buf["open"] else "▶"
                    link = f'<a href="toggle:{source}">{arrow} Raw {html.escape(source)}</a>'
                    if buf["open"]:
                        raw_html = f"<pre>{html.escape(buf['text'])}</pre>"
                        rendered.append(f"{link}<br>{raw_html}")
                    else:
                        rendered.append(link)
                else:
                    role = entry.get("role", "")
                    text = entry.get("text", "")
                    loading = entry.get("loading", False)
                    prefix = f"<b>{html.escape(role)}:</b> "
                    body = f"⏳ {html.escape(text)}" if loading else html.escape(text)
                    color = "#888" if role == "Event" else "#000"
                    rendered.append(f'<span style="color:{color}">{prefix}{body}</span>')
            self.chat_view.setHtml("<br>".join(rendered))

        def _send_message(self) -> None:
            text = self.chat_input.text().strip()
            if not text:
                return
            self._append_chat_only_user(text)
            self.chat_input.clear()
            if self.orchestrator is None:
                self._append_chat("Agent", "Kein Orchestrator verbunden.", loading=False)
                return
            if self._worker_thread and self._worker_thread.is_alive():
                self._append_chat("Agent", "Bitte warten, laufender Auftrag.", loading=False)
                return
            self._append_chat("Agent", "Antwort wird generiert ...", loading=True)
            self._worker_thread = threading.Thread(
                target=self._run_task, args=(text,), daemon=True
            )
            self._worker_thread.start()
            QTimer.singleShot(200, self._poll_results)

        def _run_task(self, description: str) -> None:
            try:
                result = self.orchestrator.run(description)
                summary = result.get("summary", {}).get("summary", "")
                self._run_queue.put(("ok", summary))
            except Exception as exc:  # pragma: no cover - UI path
                self._run_queue.put(("err", str(exc)))

        def _poll_results(self) -> None:
            # flush events first
            while True:
                try:
                    evt, payload = self._event_queue.get_nowait()
                    step = payload.get("step_id") or ""
                    status = payload.get("status") or ""
                    msg = f"{evt} {step} {status}".strip()
                    self._append_chat("Event", msg)
                except queue.Empty:
                    break
            # flush stream chunks
            flushed = False
            while True:
                try:
                    source, chunk = self._stream_queue.get_nowait()
                    self._ensure_stream_entry(source)
                    self.stream_buffers[source]["text"] += chunk
                    flushed = True
                except queue.Empty:
                    break
            if flushed:
                self._render_chat()
            try:
                status, payload = self._run_queue.get_nowait()
                if status == "ok":
                    self._append_chat("Agent", payload or "Fertig.")
                else:
                    self._append_chat("Agent", f"Fehler: {payload}")
            except queue.Empty:
                QTimer.singleShot(200, self._poll_results)

    app: Optional[QApplication] = QApplication.instance()
    app = app or QApplication([])
    window = MainWindow(
        app_title,
        status_text,
        workspace_path,
        task_description,
        plan_steps,
        language,
        models,
    )
    window.show()
    app.exec()
