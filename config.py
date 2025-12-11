import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"

ENCODING = "utf-8-sig"  # tolerates BOM on read/write

STATE_PATH = BASE_DIR / "agent_state.json"
TOOLS_META_PATH = BASE_DIR / "tools.json"
TOOLS_PY_PATH = BASE_DIR / "tools.py"
PLANNER_SYSTEM_PROMPT = PROMPTS_DIR / "planner_system_prompt.txt"
EXECUTOR_SYSTEM_PROMPT = PROMPTS_DIR / "executor_system_prompt.txt"
VALIDATOR_SYSTEM_PROMPT = PROMPTS_DIR / "validator_system_prompt.txt"
ERRORS_DIR = BASE_DIR / "errors"

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "ministral-3:14b")
EXECUTOR_MODEL = os.environ.get("EXECUTOR_MODEL", DEFAULT_MODEL)
VALIDATOR_MODEL = os.environ.get("VALIDATOR_MODEL", DEFAULT_MODEL)

MAX_PLAN_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "8"))
MAX_EXECUTOR_RETRIES = int(os.environ.get("EXECUTOR_MAX_RETRIES", "3"))
MAX_JSON_REPAIR_RETRIES = int(os.environ.get("JSON_REPAIR_RETRIES", "2"))
