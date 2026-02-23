"""
视频解析完整流程测试
测试：音轨提取 -> ASR语音识别 -> 关键帧抽取 -> 向量数据库存储
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env 文件
load_dotenv(project_root / ".env")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_video_parsing(video_path: str, user_id: int = 1):
    """
    测试视频解析完整流程

    Args:
        video_path: 视频文件路径
        user_id: 测试用户 ID
    """
    logger.info("=" * 60)
    logger.info("开始视频解析完整流程测试")
    logger.info("=" * 60)

    # 1. 检查视频文件
    video_file = Path(video_path)
    if not video_file.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return

    logger.info(f"测试视频: {video_file.name}")
    logger.info(f"文件大小: {video_file.stat().st_size / 1024 / 1024:.2f} MB")

    # 2. 导入所需模块
    from app.services.parsers.video_parser import VideoParser
    from app.services.rag.vector_store import VectorStore

    # 3. 初始化 VideoParser
    logger.info("\n[1/4] 初始化 VideoParser...")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("未设置 DASHSCOPE_API_KEY，ASR 功能将被跳过")

    parser = VideoParser(
        output_dir="media/extracted",
        interval_seconds=5,  # 每5秒抽取一帧
        api_key=api_key
    )

    # 4. 解析视频
    logger.info("\n[2/4] 解析视频（关键帧 + ASR）...")
    start_time = datetime.now()
    result = await parser.parse(video_file)
    parse_duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"解析完成，耗时: {parse_duration:.2f}秒")
    logger.info(f"提取文本块数: {len(result.chunks)}")
    logger.info(f"提取图片数: {len(result.images)}")

    # 5. 显示解析结果详情
    logger.info("\n" + "=" * 60)
    logger.info("解析结果详情:")
    logger.info("=" * 60)

    for i, chunk in enumerate(result.chunks):
        metadata = chunk.metadata
        chunk_type = metadata.get("type", "unknown")
        logger.info(f"\n--- 文本块 {i+1} [{chunk_type}] ---")
        logger.info(f"内容: {chunk.content[:100]}..." if len(chunk.content) > 100 else f"内容: {chunk.content}")

        if chunk_type == "video":
            logger.info(f"  时间戳: {metadata.get('timestamp')}")
            logger.info(f"  帧号: {metadata.get('frame_number')}")
        elif chunk_type == "audio":
            logger.info(f"  开始时间: {metadata.get('start_time'):.2f}s")
            logger.info(f"  结束时间: {metadata.get('end_time'):.2f}s")

    # 6. 存入向量数据库
    if result.chunks:
        logger.info("\n[3/4] 存入向量数据库...")

        # 检查 Embedding API Key
        if not api_key:
            logger.warning("未设置 DASHSCOPE_API_KEY，跳过向量存储")
            logger.info("\n" + "=" * 60)
            logger.info("测试完成（跳过向量存储）")
            logger.info("=" * 60)
            return

        try:
            # 初始化向量存储
            vector_store = VectorStore(
                collection_name=f"test_video_{user_id}",
                embedding_model="tongyi-embedding-vision-flash"
            )

            # 添加文档
            add_count = vector_store.add_documents(result.chunks, user_id=user_id)

            logger.info(f"成功添加 {add_count} 个文档到向量库")

            # 7. 测试检索
            logger.info("\n[4/4] 测试向量检索...")

            # 简单检索测试
            test_queries = [
                "视频内容",
                "语音",
            ]

            for query in test_queries:
                results = vector_store.similarity_search(
                    query=query,
                    user_id=user_id,
                    k=3
                )
                logger.info(f"\n查询: '{query}'")
                logger.info(f"检索到 {len(results)} 条结果:")
                for j, doc in enumerate(results):
                    logger.info(f"  {j+1}. {doc.page_content[:80]}...")

            # 显示向量库状态
            info = vector_store.get_collection_info()
            logger.info(f"\n向量库状态: {info}")

        except Exception as e:
            logger.error(f"向量存储失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("无文本块可存储")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


def main():
    """主函数"""
    # 从命令行参数或环境变量获取视频路径
    video_path = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TEST_VIDEO_PATH")

    if not video_path:
        print("用法: python -m tests.test_video_parser <视频文件路径>")
        print("或设置环境变量: export TEST_VIDEO_PATH=/path/to/video.mp4")
        print("\n示例:")
        print("  python -m tests.test_video_parser ./test_video.mp4")
        sys.exit(1)

    # 运行异步测试
    asyncio.run(test_video_parsing(video_path))


if __name__ == "__main__":
    main()
