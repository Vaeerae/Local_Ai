from task_module import run_task
from pathlib import Path
import os

def test_run_task():
    p = Path(run_task('output.txt', 'ok'))
    assert p.read_text(encoding='utf-8') == 'ok'
    assert p.name == 'output.txt'
