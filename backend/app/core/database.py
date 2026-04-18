"""
数据库连接和会话管理
"""
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""
    pass


# 创建异步引擎
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_teaching"
)


def _build_engine_kwargs() -> dict:
    kwargs = {
        "echo": os.getenv("DEBUG", "false").lower() == "true",
    }

    # Windows + asyncpg 在长连接池复用/预 ping 场景下容易出现底层 socket 异常，
    # 开发环境改用 NullPool 让每次请求使用新连接，稳定性更高。
    if sys.platform.startswith("win") and DATABASE_URL.startswith("postgresql+asyncpg://"):
        kwargs["poolclass"] = NullPool
        return kwargs

    kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )
    return kwargs


engine = create_async_engine(
    DATABASE_URL,
    **_build_engine_kwargs(),
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖函数"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库，创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
