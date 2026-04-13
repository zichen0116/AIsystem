"""
Dispatch rehearsal upload processing with a local subprocess fallback.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_running_session_keys: set[str] = set()
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def should_use_local_rehearsal_dispatch(platform: str | None = None) -> bool:
    current = platform or sys.platform
    return current.startswith("win")


def _build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    backend_root = str(_BACKEND_ROOT)
    env["PYTHONPATH"] = (
        backend_root
        if not current_pythonpath
        else f"{backend_root}{os.pathsep}{current_pythonpath}"
    )
    return env


def _session_key(session_id: int, user_id: int) -> str:
    return f"{session_id}:{user_id}"


def _schedule_local_subprocess(session_id: int, user_id: int) -> bool:
    key = _session_key(session_id, user_id)
    if key in _running_session_keys:
        return False

    _running_session_keys.add(key)
    command = [
        sys.executable,
        "-m",
        "app.rehearsal_task_runner",
        "--session-id",
        str(session_id),
        "--user-id",
        str(user_id),
    ]

    try:
        kwargs = {
            "cwd": str(_BACKEND_ROOT),
            "env": _build_subprocess_env(),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(command, **kwargs)
        return True
    except Exception:
        logger.exception(
            "Failed to spawn rehearsal local task subprocess: session_id=%s user_id=%s",
            session_id,
            user_id,
        )
        _running_session_keys.discard(key)
        return False


def _dispatch_via_celery(session_id: int, user_id: int) -> bool:
    from app.rehearsal_tasks import process_rehearsal_upload_session

    process_rehearsal_upload_session.delay(session_id, user_id)
    return True


def dispatch_rehearsal_upload_processing_task(
    session_id: int,
    user_id: int,
    platform: str | None = None,
) -> bool:
    if should_use_local_rehearsal_dispatch(platform):
        return _schedule_local_subprocess(session_id, user_id)

    try:
        return _dispatch_via_celery(session_id, user_id)
    except Exception:
        logger.exception(
            "Falling back to local rehearsal subprocess dispatch: session_id=%s user_id=%s",
            session_id,
            user_id,
        )
        return _schedule_local_subprocess(session_id, user_id)
