from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from app.core.config import settings


@dataclass(frozen=True)
class StoredFile:
    file_id: str
    path: Path
    meta_path: Path


def _root_upload_dir() -> Path:
    return Path(settings.DATA_ANALYSIS_UPLOAD_DIR)


def _root_output_dir() -> Path:
    return Path(settings.DATA_ANALYSIS_OUTPUT_DIR)


def ensure_dirs() -> None:
    _root_upload_dir().mkdir(parents=True, exist_ok=True)
    _root_output_dir().mkdir(parents=True, exist_ok=True)

def _scope_dir(scope: Union[int, str]) -> str:
    return str(scope)

def save_upload(file_id: str, filename: str, content_bytes: bytes, scope: Union[int, str]) -> StoredFile:
    ensure_dirs()
    # 以 scope 分目录（可为 user_id 或 public/anon），避免冲突
    scope_dir = _root_upload_dir() / _scope_dir(scope)
    scope_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".xlsx"
    path = scope_dir / f"{file_id}{ext}"
    meta_path = scope_dir / f"{file_id}.json"
    path.write_bytes(content_bytes)
    meta_path.write_text(
        json.dumps({"file_id": file_id, "filename": filename, "scope": _scope_dir(scope)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return StoredFile(file_id=file_id, path=path, meta_path=meta_path)

def read_meta(file_id: str, scope: Union[int, str]) -> dict[str, Any]:
    scope_dir = _root_upload_dir() / _scope_dir(scope)
    meta_path = scope_dir / f"{file_id}.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_meta(file_id: str, scope: Union[int, str], data: dict[str, Any]) -> None:
    scope_dir = _root_upload_dir() / _scope_dir(scope)
    scope_dir.mkdir(parents=True, exist_ok=True)
    meta_path = scope_dir / f"{file_id}.json"
    meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_upload_path(file_id: str, scope: Union[int, str]) -> Path:
    scope_dir = _root_upload_dir() / _scope_dir(scope)
    # 允许 .xlsx/.xlsm/.xls 等多后缀，优先常见
    for ext in [".xlsx", ".xls", ".xlsm", ".xlsb"]:
        p = scope_dir / f"{file_id}{ext}"
        if p.exists():
            return p
    # 兜底：匹配任意后缀
    for p in scope_dir.glob(f"{file_id}.*"):
        if p.is_file() and p.suffix.lower() != ".json":
            return p
    raise FileNotFoundError("上传文件不存在或无权限访问")


def save_output(task_id: str, scope: Union[int, str], filename: str, content_bytes: bytes) -> str:
    ensure_dirs()
    out_dir = _root_output_dir() / _scope_dir(scope) / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(content_bytes)
    # 返回相对 media 的路径片段（用于拼 URL）
    return str(out_path).replace("\\", "/")


def write_output_text(task_id: str, scope: Union[int, str], filename: str, text: str) -> str:
    ensure_dirs()
    out_dir = _root_output_dir() / _scope_dir(scope) / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(text, encoding="utf-8")
    return str(out_path).replace("\\", "/")


def output_file_path(task_id: str, scope: Union[int, str], filename: str) -> Path:
    return _root_output_dir() / _scope_dir(scope) / task_id / filename

