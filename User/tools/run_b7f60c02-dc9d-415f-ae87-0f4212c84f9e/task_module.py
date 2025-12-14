from pathlib import Path
import os

def run_task(filename: str = 'output.txt', content: str = 'ok'):
    """Write content to USER_DATA_DIR/filename and return path."""
    data_dir = Path(os.environ.get('USER_DATA_DIR', '.'))
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / filename
    target.write_text(content, encoding='utf-8')
    return str(target)
