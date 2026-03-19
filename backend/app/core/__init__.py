"""
核心模块导出。
"""

__all__ = ["settings", "get_settings"]


def __getattr__(name: str):
    if name in {"settings", "get_settings"}:
        from app.core.config import get_settings, settings

        return {
            "settings": settings,
            "get_settings": get_settings,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
