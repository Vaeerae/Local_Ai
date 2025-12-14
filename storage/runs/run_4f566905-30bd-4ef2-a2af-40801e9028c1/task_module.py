def run_task(path: str = 'output.txt', content: str = 'ok'):
    """Write content to a file and return path."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path
