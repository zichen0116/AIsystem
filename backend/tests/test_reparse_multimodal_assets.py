from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "reparse_multimodal_assets.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("reparse_multimodal_assets", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_normalize_requested_types_maps_extensions_to_multimodal_groups():
    module = load_script_module()

    normalized = module.normalize_requested_types([".png", "image", "mp4", "video"])

    assert normalized == {"image", "video"}


def test_build_asset_type_filter_rejects_empty_input():
    module = load_script_module()

    with pytest.raises(ValueError):
        module.normalize_requested_types([])
