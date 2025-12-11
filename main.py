import os
from pathlib import Path

from config import STATE_PATH
from orchestrator import run_full_cycle
from state import ProjectState


def main() -> None:
    if not Path(STATE_PATH).exists():
        print("[INFO] Keine bestehende agent_state.json gefunden, es wird ein neuer Projektzustand angelegt.")
        ProjectState().save()

    print("Selbst-erweiternder Multi-Agent (Planner / Executor / Validator)")
    print("Gib eine Aufgabe ein. Mit 'exit' oder 'quit' beenden.\n")

    while True:
        try:
            user_input = input("Du: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTschuess.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Tschuess.")
            break

        if not user_input:
            continue

        run_full_cycle(user_input)


if __name__ == "__main__":
    main()
