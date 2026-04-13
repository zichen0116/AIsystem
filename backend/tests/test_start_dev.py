import start_dev


def test_build_celery_worker_command_uses_solo_pool_on_windows():
    command = start_dev.build_celery_worker_command('python', platform='win32')

    assert command[:6] == ['python', '-m', 'celery', '-A', 'app.celery', 'worker']
    assert '--pool=solo' in command
    assert '--concurrency=1' in command


def test_build_celery_worker_command_keeps_default_pool_on_linux():
    command = start_dev.build_celery_worker_command('python', platform='linux')

    assert '--pool=solo' not in command
    assert '--concurrency=1' not in command


def test_build_child_process_env_sets_unbuffered_python():
    env = start_dev.build_child_process_env({'EXISTING': '1'})

    assert env['EXISTING'] == '1'
    assert env['PYTHONUNBUFFERED'] == '1'


def test_start_process_uses_inherited_stdio(monkeypatch):
    recorded = {}

    class FakeProcess:
        pass

    def fake_popen(command, **kwargs):
        recorded['command'] = command
        recorded['kwargs'] = kwargs
        return FakeProcess()

    monkeypatch.setattr(start_dev.subprocess, 'Popen', fake_popen)

    manager = start_dev.ProcessManager()
    manager.start_process('FastAPI', ['python', 'run.py'], cwd='D:/tmp')

    assert recorded['command'] == ['python', 'run.py']
    assert recorded['kwargs']['cwd'] == 'D:/tmp'
    assert recorded['kwargs']['env']['PYTHONUNBUFFERED'] == '1'
    assert 'stdout' not in recorded['kwargs']
    assert 'stderr' not in recorded['kwargs']
