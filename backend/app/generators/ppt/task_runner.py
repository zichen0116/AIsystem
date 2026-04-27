"""
Run PPT background tasks in a standalone Python process.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    backend_root = Path(__file__).resolve().parents[3]
    load_dotenv(backend_root / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone runner for PPT background tasks")
    subparsers = parser.add_subparsers(dest="task_type", required=True)

    file_gen = subparsers.add_parser("file_generation")
    file_gen.add_argument("--project-id", type=int, required=True)
    file_gen.add_argument("--task-id", required=True)
    file_gen.add_argument("--file-id", type=int)
    file_gen.add_argument("--source-text")

    renovation = subparsers.add_parser("renovation_parse")
    renovation.add_argument("--project-id", type=int, required=True)
    renovation.add_argument("--task-id", required=True)
    renovation.add_argument("--file-id", type=int, required=True)

    reference = subparsers.add_parser("reference_parse")
    reference.add_argument("--project-id", type=int, required=True)
    reference.add_argument("--task-id", required=True)
    reference.add_argument("--file-id", type=int, required=True)

    args = parser.parse_args()
    _load_env()

    if args.task_type == "file_generation":
        from app.generators.ppt.celery_tasks import file_generation_task

        file_generation_task.apply(
            kwargs={
                "project_id": args.project_id,
                "file_id": args.file_id,
                "source_text": args.source_text,
                "task_id_str": args.task_id,
            },
            throw=False,
        )
        return 0

    if args.task_type == "renovation_parse":
        from app.generators.ppt.celery_tasks import renovation_parse_task

        renovation_parse_task.apply(
            kwargs={
                "project_id": args.project_id,
                "file_id": args.file_id,
                "task_id_str": args.task_id,
            },
            throw=False,
        )
        return 0

    if args.task_type == "reference_parse":
        from app.generators.ppt.celery_tasks import reference_parse_task

        reference_parse_task.apply(
            kwargs={
                "project_id": args.project_id,
                "file_id": args.file_id,
                "task_id_str": args.task_id,
            },
            throw=False,
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
