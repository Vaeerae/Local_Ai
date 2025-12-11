# Automatisch generiertes Tools-Modul

TOOL_REGISTRY = {}


import json
import os

def create_architecture_json(output_path, structure):
    # Strukturierte Daten für die Architektur- und Komponentenübersicht
    architecture_data = {
        "UI-Komponenten": {
            "folder_tree": {
                "description": "PyQt6-QTreeView-basierte Ordnerbaum-UI mit Pfadnavigation und Kontextmenü (z. B. für Dateioperationen).",
                "dependencies": ["PyQt6", "QTreeView", "QFileSystemModel"]
            },
            "chat_interface": {
                "description": "Chat-Fenster mit QTextEdit für Benutzereingaben und QPlainTextEdit für Antworten (mit Scrollbar und dynamischer Anpassung).",
                "dependencies": ["PyQt6", "QTextEdit", "QPlainTextEdit"]
            },
            "installation_dialog": {
                "description": "Startdialog zur Modellauswahl mit Warnung bei fehlender Ollama-Installation (QDialog-basiert).",
                "dependencies": ["PyQt6", "QDialog", "QMessageBox"]
            },
            "settings_dialog": {
                "description": "Einstellungsoberfläche für Modelländerung und Speicherpfad-Konfiguration (QWidget-basiert).",
                "dependencies": ["PyQt6", "QWidget", "QSettings"]
            }
        },
        "Backend-Komponenten": {
            "ollama_integration": {
                "description": "API-Aufrufe an Ollama (http://localhost:11434/api/generate) mit Fehlerbehandlung für Timeout und fehlende Modelle.",
                "dependencies": ["requests", "timeout", "json"]
            },
            "config_manager": {
                "description": "Klasse zum Laden/Speichern der Konfiguration (settings.json) mit Schlüsseln wie model_name und ollama_path.",
                "dependencies": ["json", "os"]
            },
            "installation_checker": {
                "description": "Funktion zur Prüfung der Ollama-Installation durch Port-Test (11434) und Modellverfügbarkeit.",
                "dependencies": ["socket", "requests"]
            }
        },
        "Dateistruktur": {
            "project_root": {
                "description": "Hauptverzeichnis mit Unterordern src/, config/ und dist/.",
                "structure": {
                    "src": {
                        "ui": "UI-Komponenten (z. B. main_window.py, dialogs.py)",
                        "backend": "Backend-Logik (z. B. ollama_api.py, config_manager.py)",
                        "utils": "Hilfsfunktionen (z. B. helpers.py)"
                    },
                    "config": "Konfigurationsdateien (z. B. settings.json)",
                    "dist": "Installationsausgabe (z. B. verpackte .exe-Datei)"
                }
            }
        },
        "Abhängigkeiten": {
            "requirements.txt": ["PyQt6==6.4.0", "requests==2.31.0", "PyInstaller==6.1.0"],
            "ollama_api": {
                "generate": "POST /api/generate (Parameter: model, prompt, stream)",
                "models": "GET /api/tags (Liste verfügbarer Modelle)"
            }
        },
        "Installationsprozess": {
            "pyinstaller_command": "pyinstaller --onefile --windowed --add-data "config;config" --add-data "ui;ui" main.py",
            "post_install_guide": [
                "1. Ollama installieren: https://ollama.ai",
                "2. Modell herunterladen: ollama pull [MODELLNAME]",
                "3. Anwendung starten und Modell im Einstellungsdialog auswählen"
            ]
        }
    }
    
    # Verzeichnis erstellen, falls nicht vorhanden
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # JSON-Dokument speichern
    with open(output_path, 'w') as f:
        json.dump(architecture_data, f, indent=4)
    
    return output_path
TOOL_REGISTRY["create_architecture_json"] = create_architecture_json
