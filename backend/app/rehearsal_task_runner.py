"""
Run rehearsal upload processing in a standalone Python process.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone runner for rehearsal upload processing")
    parser.add_argument("--session-id", type=int, required=True)
    parser.add_argument("--user-id", type=int, required=True)
    args = parser.parse_args()
    _load_env()

    from app.rehearsal_tasks import process_rehearsal_upload_session

    process_rehearsal_upload_session.apply(
        args=[args.session_id, args.user_id],
        throw=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
