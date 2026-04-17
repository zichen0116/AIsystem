"""
Dispatch PPT tasks in a separate Python subprocess so local/dev environments
can run them reliably even when Celery broker/worker wiring is unavailable.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators.ppt.banana_models import PPTProject, PPTReferenceFile, PPTTask

logger = logging.getLogger(__name__)

_running_task_ids: set[str] = set()
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


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


def _schedule_local_subprocess(task_id: str, args: list[str], task_type: str) -> bool:
    if not task_id or task_id in _running_task_ids:
        return False

    _running_task_ids.add(task_id)

    async def _run() -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "app.generators.ppt.task_runner",
                *args,
                cwd=str(_BACKEND_ROOT),
                env=_build_subprocess_env(),
            )
            exit_code = await proc.wait()
            if exit_code != 0:
                logger.error(
                    "PPT local task subprocess exited abnormally: task_id=%s task_type=%s code=%s",
                    task_id,
                    task_type,
                    exit_code,
                )
        except Exception:
            logger.exception("Failed to spawn PPT local task subprocess: task_id=%s task_type=%s", task_id, task_type)
        finally:
            _running_task_ids.discard(task_id)

    asyncio.create_task(_run())
    return True


def dispatch_file_generation_task(*, project_id: int, task_id_str: str, file_id: int | None, source_text: str | None) -> bool:
    args = [
        "file_generation",
        "--project-id", str(project_id),
        "--task-id", task_id_str,
    ]
    if file_id is not None:
        args.extend(["--file-id", str(file_id)])
    if source_text:
        args.extend(["--source-text", source_text])
    return _schedule_local_subprocess(task_id_str, args, "file_generation")


def dispatch_renovation_parse_task(*, project_id: int, file_id: int, task_id_str: str) -> bool:
    args = [
        "renovation_parse",
        "--project-id", str(project_id),
        "--file-id", str(file_id),
        "--task-id", task_id_str,
    ]
    return _schedule_local_subprocess(task_id_str, args, "renovation_parse")


async def ensure_pending_task_started(db: AsyncSession, task: PPTTask) -> bool:
    if not task or task.status != "PENDING" or task.task_id in _running_task_ids:
        return False

    if task.task_type == "file_generation":
        project_res = await db.execute(select(PPTProject).where(PPTProject.id == task.project_id))
        project = project_res.scalar_one_or_none()
        if not project:
            return False

        ref_res = await db.execute(
            select(PPTReferenceFile.id)
            .where(PPTReferenceFile.project_id == task.project_id)
            .order_by(PPTReferenceFile.id.desc())
            .limit(1)
        )
        file_id = ref_res.scalar_one_or_none()
        source_text = str((project.settings or {}).get("file_generation_source_text") or "").strip() or None
        return dispatch_file_generation_task(
            project_id=task.project_id,
            task_id_str=task.task_id,
            file_id=file_id,
            source_text=source_text,
        )

    if task.task_type == "renovation_parse":
        ref_res = await db.execute(
            select(PPTReferenceFile.id)
            .where(PPTReferenceFile.project_id == task.project_id)
            .order_by(PPTReferenceFile.id.desc())
            .limit(1)
        )
        file_id = ref_res.scalar_one_or_none()
        if file_id is None:
            return False
        return dispatch_renovation_parse_task(
            project_id=task.project_id,
            file_id=file_id,
            task_id_str=task.task_id,
        )

    return False
