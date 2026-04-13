import app.rehearsal_task_dispatcher as dispatcher


def test_dispatch_rehearsal_upload_processing_uses_local_subprocess_on_windows(monkeypatch):
    scheduled = []

    monkeypatch.setattr(
        dispatcher,
        '_schedule_local_subprocess',
        lambda session_id, user_id: scheduled.append((session_id, user_id)) or True,
    )

    result = dispatcher.dispatch_rehearsal_upload_processing_task(11, 7, platform='win32')

    assert result is True
    assert scheduled == [(11, 7)]


def test_dispatch_rehearsal_upload_processing_falls_back_when_celery_send_fails(monkeypatch):
    scheduled = []

    def fail_dispatch(_session_id, _user_id):
        raise RuntimeError('broker unavailable')

    monkeypatch.setattr(dispatcher, '_dispatch_via_celery', fail_dispatch)
    monkeypatch.setattr(
        dispatcher,
        '_schedule_local_subprocess',
        lambda session_id, user_id: scheduled.append((session_id, user_id)) or True,
    )

    result = dispatcher.dispatch_rehearsal_upload_processing_task(13, 5, platform='linux')

    assert result is True
    assert scheduled == [(13, 5)]


def test_schedule_local_subprocess_uses_popen_without_running_event_loop(monkeypatch):
    recorded = {}

    class FakeProcess:
        pass

    def fake_popen(command, **kwargs):
        recorded['command'] = command
        recorded['kwargs'] = kwargs
        return FakeProcess()

    monkeypatch.setattr(dispatcher.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(dispatcher.sys, 'executable', 'python')
    dispatcher._running_session_keys.clear()

    result = dispatcher._schedule_local_subprocess(23, 3)

    assert result is True
    assert recorded['command'][:3] == ['python', '-m', 'app.rehearsal_task_runner']
    assert recorded['kwargs']['cwd'] == str(dispatcher._BACKEND_ROOT)
