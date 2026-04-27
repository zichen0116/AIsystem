from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select

from app.models.knowledge_asset import KnowledgeAsset


IMAGE_TYPE_HINTS = {
    "image",
    "img",
    "jpg",
    "jpeg",
    "png",
    "bmp",
    "gif",
    "webp",
}
VIDEO_TYPE_HINTS = {
    "video",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "flv",
    "wmv",
    "webm",
}


def normalize_asset_type(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if not normalized:
        return None

    if normalized.startswith("."):
        normalized = normalized[1:]

    if normalized in IMAGE_TYPE_HINTS:
        return "image"
    if normalized in VIDEO_TYPE_HINTS:
        return "video"
    return normalized


def normalize_requested_types(values: Iterable[str]) -> set[str]:
    normalized_types: set[str] = set()

    for raw in values:
        for piece in str(raw).split(","):
            normalized = normalize_asset_type(piece)
            if normalized in {"image", "video"}:
                normalized_types.add(normalized)

    if not normalized_types:
        raise ValueError("At least one supported multimodal type is required: image, video")

    return normalized_types


def iter_target_assets(*, library_id: int | None, asset_id: int | None, target_types: set[str]):
    from app.tasks import get_sync_db

    db = get_sync_db()
    try:
        stmt = select(KnowledgeAsset).order_by(KnowledgeAsset.id.asc())
        if library_id is not None:
            stmt = stmt.where(KnowledgeAsset.library_id == library_id)
        if asset_id is not None:
            stmt = stmt.where(KnowledgeAsset.id == asset_id)

        assets = db.execute(stmt).scalars().all()
        for asset in assets:
            if normalize_asset_type(asset.file_type) in target_types:
                yield asset
    finally:
        db.close()


def reparse_assets(*, library_id: int | None, asset_id: int | None, target_types: set[str], dry_run: bool = False) -> dict:
    from app.services.rag.vector_store import VectorStore
    from app.tasks import processor

    targets = list(iter_target_assets(library_id=library_id, asset_id=asset_id, target_types=target_types))
    if not targets:
        return {"matched": 0, "processed": 0, "failed": 0, "results": []}

    vector_store = VectorStore()
    results: list[dict] = []
    processed = 0
    failed = 0

    for asset in targets:
        item = {
            "asset_id": asset.id,
            "library_id": asset.library_id,
            "file_name": asset.file_name,
            "file_type": asset.file_type,
        }
        if dry_run:
            item["status"] = "dry_run"
            results.append(item)
            continue

        try:
            vector_store.delete_asset_documents(asset.id, asset.library_id)
            process_result = processor.process(asset.id, asset.user_id, asset.library_id)
            item["status"] = "success"
            item["result"] = process_result
            processed += 1
        except Exception as exc:  # pragma: no cover - CLI safety net
            item["status"] = "failed"
            item["error"] = str(exc)
            failed += 1
        results.append(item)

    return {
        "matched": len(targets),
        "processed": processed,
        "failed": failed,
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reparse multimodal knowledge assets with the latest shared image/video parsers."
    )
    parser.add_argument("--library-id", type=int, default=None, help="Only reparse assets from this library")
    parser.add_argument("--asset-id", type=int, default=None, help="Only reparse this asset")
    parser.add_argument(
        "--types",
        nargs="+",
        default=["image,video"],
        help="Target multimodal types, for example: image video or image,video",
    )
    parser.add_argument("--dry-run", action="store_true", help="List matched assets without reparsing them")
    args = parser.parse_args()

    if args.library_id is None and args.asset_id is None:
        parser.error("At least one of --library-id or --asset-id is required")

    return args


def main() -> int:
    args = parse_args()
    target_types = normalize_requested_types(args.types)
    summary = reparse_assets(
        library_id=args.library_id,
        asset_id=args.asset_id,
        target_types=target_types,
        dry_run=args.dry_run,
    )

    print(
        f"matched={summary['matched']} processed={summary['processed']} failed={summary['failed']} dry_run={args.dry_run}"
    )
    for item in summary["results"]:
        message = (
            f"asset_id={item['asset_id']} "
            f"library_id={item.get('library_id')} "
            f"type={item.get('file_type')} "
            f"status={item['status']}"
        )
        if item.get("error"):
            message += f" error={item['error']}"
        print(message)

    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
