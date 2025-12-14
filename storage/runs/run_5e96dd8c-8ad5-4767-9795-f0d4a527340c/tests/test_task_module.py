from task_module import run_task

def test_run_task(tmp_path):
    target = tmp_path / 'output.txt'
    p = run_task(str(target), 'ok')
    assert target.read_text(encoding='utf-8') == 'ok'
    assert p.endswith('output.txt')
