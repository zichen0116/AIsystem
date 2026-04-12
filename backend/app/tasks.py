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
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session, selectinload
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.celery import celery_app
from app.services.parsers.factory import ParserFactory
from app.services.rag.vector_store import VectorStore
from app.services.rag.text_splitter import split_documents, split_documents_semantic
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.rehearsal import RehearsalSession
from app.services.rehearsal_file_processing_service import process_rehearsal_session_assets
from app.services.rehearsal_session_service import compute_session_status

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

    def process(self, asset_id: int, user_id: int, library_id: int | None = None) -> dict:
        """
        处理知识资产：解析 + 切片 + 向量化存储

        Args:
            asset_id: 知识资产 ID
            user_id: 用户 ID
            library_id: 知识库 ID（可选）

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

            # 更新状态为处理中
            db.execute(
                update(KnowledgeAsset)
                .where(KnowledgeAsset.id == asset_id)
                .values(vector_status="processing")
            )
            db.commit()

            file_path_str = asset.file_path
            temp_file = None

            try:
                # If file_path is an OSS URL, download to temp first
                if file_path_str.startswith("http"):
                    from app.services.oss_service import download_to_temp
                    temp_file = download_to_temp(file_path_str)
                    file_path = Path(temp_file)
                else:
                    file_path = Path(file_path_str)
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
                split_chunks = split_documents_semantic(
                    parse_result.chunks,
                    breakpoint_threshold_type="percentile",
                    breakpoint_threshold_amount=0.95,
                    min_chunk_size=100
                )
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
                    user_id=user_id,
                    library_id=library_id,
                    asset_id=asset_id
                )

                # 5. 更新数据库状态
                db.execute(
                    update(KnowledgeAsset)
                    .where(KnowledgeAsset.id == asset_id)
                    .values(
                        vector_status="completed",
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
                # Clean up temp file if downloaded from OSS (always runs, even on failure)
                if temp_file:
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

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
def process_knowledge_asset(self, asset_id: int, user_id: int, library_id: int | None = None):
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
    logger.info(f"开始处理知识资产: asset_id={asset_id}, user_id={user_id}, library_id={library_id}, retry={self.request.retries}")

    try:
        return processor.process(asset_id, user_id, library_id)

    except Exception as e:
        logger.error(f"处理知识资产失败: {e}", exc_info=True)

        # 更新失败状态
        try:
            db = get_sync_db()
            from app.models.knowledge_asset import KnowledgeAsset
            db.execute(
                update(KnowledgeAsset)
                .where(KnowledgeAsset.id == asset_id)
                .values(vector_status="failed")
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

@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_library",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5}
)
def cleanup_library(self, library_id: int):
    """
    异步清理知识库：删除向量 + 物理文件 + DB 记录
    软删除之后由此任务执行实际清理
    """
    from app.models.knowledge_library import KnowledgeLibrary
    from app.models.knowledge_asset import KnowledgeAsset
    from app.services.rag.vector_store import VectorStore
    import os

    db = get_sync_db()
    try:
        # 1. 删除 ChromaDB 向量
        vs = VectorStore()
        vs.delete_library_documents(library_id)

        # 1.5 清理 Neo4j 图谱数据（如果是系统知识库）
        try:
            lib_result = db.execute(
                select(KnowledgeLibrary).where(KnowledgeLibrary.id == library_id)
            )
            lib = lib_result.scalar_one_or_none()
            if lib and lib.is_system:
                from app.services.rag.graph_store import GraphStore
                asyncio.run(GraphStore.delete_library(library_id))
                logger.info(f"Neo4j 图谱数据清理完成: library_id={library_id}")
        except Exception as e:
            logger.warning(f"图谱清理失败（非致命）: library_id={library_id}, {e}")

        # 2. 获取所有关联文件路径
        result = db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.library_id == library_id)
        )
        assets = result.scalars().all()

        # 3. 删除文件（OSS 或本地）
        from app.services.oss_service import delete_file as oss_delete
        for asset in assets:
            try:
                if asset.file_path:
                    if asset.file_path.startswith("http"):
                        oss_delete(asset.file_path)
                    elif os.path.exists(asset.file_path):
                        os.remove(asset.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {asset.file_path}, {e}")

        # 4. 物理删除 DB 记录
        db.execute(
            delete(KnowledgeAsset).where(KnowledgeAsset.library_id == library_id)
        )
        db.execute(
            delete(KnowledgeLibrary).where(KnowledgeLibrary.id == library_id)
        )
        db.commit()

        logger.info(f"知识库 {library_id} 清理完成")
        return {"status": "success", "library_id": library_id}

    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.tasks.build_graph_index",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def build_graph_index(self, library_id: int, asset_ids: list[int]):
    """
    为系统知识库构建 LightRAG 图索引。

    从 PostgreSQL 查出指定资产的已解析文本，调用 GraphStore 插入图谱。
    去重由 LightRAG 内部的文档哈希校验自动完成。

    Args:
        library_id: 系统知识库 ID
        asset_ids: 要索引的知识资产 ID 列表
    """
    from app.models.knowledge_asset import KnowledgeAsset
    from app.services.rag.graph_store import GraphStore

    logger.info(
        f"开始构建图索引: library_id={library_id}, "
        f"asset_ids={asset_ids}, retry={self.request.retries}"
    )

    db = get_sync_db()
    try:
        # 查出已完成向量化的资产
        result = db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.id.in_(asset_ids),
                KnowledgeAsset.library_id == library_id,
                KnowledgeAsset.vector_status == "completed",
            )
        )
        assets = result.scalars().all()

        if not assets:
            logger.warning(f"未找到可索引的资产: library_id={library_id}")
            return {"status": "skipped", "message": "无可索引资产"}

        # 收集所有文本内容
        from app.services.rag.vector_store import VectorStore

        vs = VectorStore()
        all_texts = []

        # 按资产逐个获取，确保只拉取 asset_ids 指定的资产
        for asset in assets:
            try:
                docs = vs.get_documents_by_metadata(library_id, asset.id)
                all_texts.extend(docs)
            except Exception as e:
                logger.warning(
                    f"获取资产文本失败 asset_id={asset.id}: {e}"
                )

        if not all_texts:
            logger.warning(f"资产中无文本内容: library_id={library_id}")
            return {"status": "skipped", "message": "资产无文本内容"}

        logger.info(
            f"准备插入图谱: library_id={library_id}, "
            f"texts={len(all_texts)}"
        )

        # 使用 asyncio.run 桥接异步调用
        asyncio.run(GraphStore.insert_documents(library_id, all_texts))

        logger.info(f"图索引构建完成: library_id={library_id}")
        return {
            "status": "success",
            "library_id": library_id,
            "indexed_assets": len(assets),
            "total_texts": len(all_texts),
        }

    except Exception as e:
        logger.error(f"图索引构建失败: {e}", exc_info=True)
        raise

    finally:
        db.close()



async def _run_rehearsal_upload_processing(session_id: int, user_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RehearsalSession)
            .options(selectinload(RehearsalSession.scenes))
            .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            logger.warning('上传预演会话不存在: session_id=%s, user_id=%s', session_id, user_id)
            return {'status': 'missing', 'session_id': session_id}

        try:
            payload = await process_rehearsal_session_assets(db, session)
            session.status = compute_session_status(session)
            session.error_message = None
            await db.commit()
            return {
                'status': session.status,
                'session_id': session.id,
                'scene_count': payload.get('scene_count', 0),
                'converted_pdf_url': session.converted_pdf_url,
            }
        except Exception as exc:
            session.status = 'failed'
            session.error_message = str(exc)
            await db.commit()
            logger.exception('上传预演文件处理失败: session_id=%s', session_id)
            return {
                'status': 'failed',
                'session_id': session_id,
                'error_message': session.error_message,
            }


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name='app.tasks.process_rehearsal_upload_session',
)
def process_rehearsal_upload_session(self, session_id: int, user_id: int):
    """处理上传预演会话的后台文件解析链路。"""
    logger.info('开始处理上传预演会话: session_id=%s, user_id=%s', session_id, user_id)
    return asyncio.run(_run_rehearsal_upload_processing(session_id, user_id))

