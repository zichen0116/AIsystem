"""
核心模块导出
"""
# 只导出配置，其他模块按需导入避免循环依赖
from app.core.config import settings, get_settings

__all__ = [
    "settings",
    "get_settings",
]
