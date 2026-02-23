"""
Celery 异步任务
处理知识资产解析和向量化
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional

from celery import Task
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.celery import celery_app
from app.services.parsers.factory import ParserFactory
from app.services.rag.vector_store import VectorStore
from app.services.rag.text_splitter import split_documents
from app.core.config import settings

logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================
# 单个视频最多关键帧数
MAX_VIDEO_KEYFRAMES = int(os.getenv("MAX_VIDEO_KEYFRAMES", "15"))
# 单个 PDF 每页最多识别图片数
MAX_PDF_IMAGES_PER_PAGE = int(os.getenv("MAX_PDF_IMAGES_PER_PAGE", "2"))
# 单个 Word 文档最多识别图片数
MAX_WORD_IMAGES = int(os.getenv("MAX_WORD_IMAGES", "10"))


def get_sync_db():
    """获取同步数据库会话"""
    DATABASE_URL_SYNC = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:123456@127.0.0.1:5432/ai_teaching"
    )
    engine = create_engine(DATABASE_URL_SYNC)
    return Session(engine)


class CallbackTask(Task):
    """带回调的任务基类"""

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功回调"""
        logger.info(f"任务 {task_id} 成功完成: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        logger.error(f"任务 {task_id} 失败: {exc}")


class KnowledgeAssetProcessor:
    """知识资产处理器 - 包含核心处理逻辑"""

    def __init__(self):
        self._configure_parser_limits()

    def _configure_parser_limits(self):
        """配置解析器的数量限制"""
        # 设置环境变量供解析器读取
        os.environ["MAX_VIDEO_KEYFRAMES"] = str(MAX_VIDEO_KEYFRAMES)
        os.environ["MAX_PDF_IMAGES_PER_PAGE"] = str(MAX_PDF_IMAGES_PER_PAGE)
        os.environ["MAX_WORD_IMAGES"] = str(MAX_WORD_IMAGES)
        logger.info(
            f"解析器限制配置: MAX_VIDEO_KEYFRAMES={MAX_VIDEO_KEYFRAMES}, "
            f"MAX_PDF_IMAGES_PER_PAGE={MAX_PDF_IMAGES_PER_PAGE}, "
            f"MAX_WORD_IMAGES={MAX_WORD_IMAGES}"
        )

    def process(self, asset_id: int, user_id: int) -> dict:
        """
        处理知识资产：解析 + 切片 + 向量化存储

        Args:
            asset_id: 知识资产 ID
            user_id: 用户 ID

        Returns:
            dict: 处理结果
        """
        from app.models.knowledge_asset import KnowledgeAsset

        db = get_sync_db()
        try:
            # 1. 获取知识资产信息
            result = db.execute(
                select(KnowledgeAsset).where(KnowledgeAsset.id == asset_id)
            )
            asset = result.scalar_one_or_none()

            if not asset:
                raise ValueError(f"知识资产不存在: {asset_id}")

            file_path = Path(asset.file_path)
            if not file_path.exists():
                raise ValueError(f"文件不存在: {file_path}")

            # 2. 解析文件
            logger.info(f"解析文件: {file_path}")
            parse_result = asyncio.run(ParserFactory.parse_file(file_path))

            if not parse_result or not parse_result.chunks:
                raise ValueError("文件解析失败或无内容")

            image_count = len(parse_result.images)
            logger.info(f"解析完成: {len(parse_result.chunks)} 个文本块, {image_count} 张图片")

            # 3. 文本切片（语义分块 - Semantic Chunking）
            logger.info("执行语义切片...")
            # 优先使用语义分块，保持语义完整性
            split_chunks = split_documents_semantic(
                parse_result.chunks,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=0.95,
                min_chunk_size=100
            )
            # 如果语义分块失败，回退到递归分块
            if not split_chunks or len(split_chunks) < 2:
                logger.warning("语义分块结果不佳，回退到递归分块")
                split_chunks = split_documents(
                    parse_result.chunks,
                    chunk_size=800,
                    chunk_overlap=150
                )
            logger.info(f"切片完成: {len(split_chunks)} 个切片")

            # 4. 存储到向量库
            logger.info(f"存储到向量库: {len(split_chunks)} 个切片")
            vectorstore = VectorStore()
            doc_count = vectorstore.add_documents(
                split_chunks,
                user_id=user_id
            )

            # 5. 更新数据库状态
            db.execute(
                update(KnowledgeAsset)
                .where(KnowledgeAsset.id == asset_id)
                .values(
                    vector_status=True,
                    chunk_count=len(split_chunks),
                    image_count=image_count
                )
            )
            db.commit()

            logger.info(
                f"知识资产处理完成: asset_id={asset_id}, "
                f"原始chunks={len(parse_result.chunks)}, "
                f"切片后={len(split_chunks)}, "
                f"images={image_count}, "
                f"vectors={doc_count}"
            )

            return {
                "status": "success",
                "asset_id": asset_id,
                "original_chunks": len(parse_result.chunks),
                "split_chunks": len(split_chunks),
                "images": image_count,
                "vectors": doc_count
            }

        finally:
            db.close()


# 创建处理器实例
processor = KnowledgeAssetProcessor()


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.tasks.process_knowledge_asset",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3}
)
def process_knowledge_asset(self, asset_id: int, user_id: int):
    """
    处理知识资产：解析 + 切片 + 向量化存储

    带重试机制：
    - 最多重试 3 次
    - 指数退避: 1s, 2s, 4s, 8s... 最大 10 分钟
    - 处理 429 (限流) 和其他临时错误

    Args:
        asset_id: 知识资产 ID
        user_id: 用户 ID

    Returns:
        dict: 处理结果
    """
    logger.info(f"开始处理知识资产: asset_id={asset_id}, user_id={user_id}, retry={self.request.retries}")

    try:
        return processor.process(asset_id, user_id)

    except Exception as e:
        logger.error(f"处理知识资产失败: {e}", exc_info=True)

        # 更新失败状态
        try:
            db = get_sync_db()
            from app.models.knowledge_asset import KnowledgeAsset
            db.execute(
                update(KnowledgeAsset)
                .where(KnowledgeAsset.id == asset_id)
                .values(vector_status=False)
            )
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

        raise


@celery_app.task(name="app.tasks.cleanup_temp_files")
def cleanup_temp_files():
    """
    清理临时文件

    定期执行，清理已处理完成的临时文件
    注意：不会清理知识资产关联的图片
    """
    import shutil
    import time

    # 只清理超过 7 天的临时文件
    extracted_dir = Path("media/temp")
    if extracted_dir.exists():
        try:
            cutoff = time.time() - (7 * 24 * 60 * 60)

            for file in extracted_dir.rglob("*"):
                if file.is_file():
                    if file.stat().st_mtime < cutoff:
                        file.unlink()
                        logger.info(f"删除临时文件: {file}")

            return {"status": "success", "message": "临时文件清理完成"}
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "success", "message": "无临时文件"}


@celery_app.task(name="app.tasks.cleanup_orphaned_images")
def cleanup_orphaned_images():
    """
    清理孤立图片

    定期执行，清理没有被任何知识资产引用的图片
    """
    from app.models.knowledge_asset import KnowledgeAsset

    db = get_sync_db()
    try:
        # 获取所有知识资产关联的图片数量
        result = db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.image_count > 0)
        )
        assets = result.scalars().all()

        total_images = sum(asset.image_count or 0 for asset in assets)

        logger.info(f"知识资产关联图片总数: {total_images}")

        return {
            "status": "success",
            "total_assets": len(assets),
            "total_images": total_images
        }

    finally:
        db.close()
