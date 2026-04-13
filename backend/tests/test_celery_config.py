import app.celery as celery_module


def test_get_platform_worker_settings_uses_solo_pool_on_windows():
    assert celery_module.get_platform_worker_settings('win32') == {
        'worker_pool': 'solo',
        'worker_concurrency': 1,
    }


def test_get_platform_worker_settings_keeps_default_pool_on_linux():
    assert celery_module.get_platform_worker_settings('linux') == {}
