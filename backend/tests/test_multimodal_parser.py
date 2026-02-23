"""
多模态解析测试
测试：图片解析 + 视频解析（关键帧视觉理解 + 感知哈希去重）
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


async def test_image_parser(image_path: str):
    """
    测试 ImageParser 图片解析

    Args:
        image_path: 图片文件路径
    """
    logger.info("=" * 60)
    logger.info("测试 ImageParser 图片解析")
    logger.info("=" * 60)

    image_file = Path(image_path)
    if not image_file.exists():
        logger.error(f"图片文件不存在: {image_path}")
        return

    logger.info(f"测试图片: {image_file.name}")
    logger.info(f"文件大小: {image_file.stat().st_size / 1024:.2f} KB")

    # 导入 ImageParser
    from app.services.parsers.image_parser import ImageParser
    from app.services.parsers.factory import ParserFactory

    # 方法1: 直接使用 ImageParser
    logger.info("\n[方法1] 直接使用 ImageParser...")
    api_key = os.getenv("DASHSCOPE_API_KEY")

    parser = ImageParser(api_key=api_key)
    result = await parser.parse(image_file)

    logger.info(f"解析完成:")
    logger.info(f"  文本块数: {len(result.chunks)}")
    logger.info(f"  图片数: {len(result.images)}")

    for i, chunk in enumerate(result.chunks):
        logger.info(f"\n--- 文本块 {i+1} ---")
        logger.info(f"  类型: {chunk.metadata.get('type')}")
        logger.info(f"  来源: {chunk.metadata.get('source')}")
        content = chunk.content
        if len(content) > 200:
            logger.info(f"  内容: {content[:200]}...")
        else:
            logger.info(f"  内容: {content}")

    # 方法2: 使用 ParserFactory
    logger.info("\n[方法2] 使用 ParserFactory...")
    result2 = await ParserFactory.parse_file(image_file)

    logger.info(f"解析完成:")
    logger.info(f"  文本块数: {len(result2.chunks)}")

    logger.info("\n" + "=" * 60)
    logger.info("ImageParser 测试完成")
    logger.info("=" * 60)


async def test_video_parser_with_vision(video_path: str):
    """
    测试 VideoParser 视频解析（带视觉理解）

    Args:
        video_path: 视频文件路径
    """
    logger.info("=" * 60)
    logger.info("测试 VideoParser 视频解析（视觉理解 + 感知哈希去重）")
    logger.info("=" * 60)

    video_file = Path(video_path)
    if not video_file.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return

    logger.info(f"测试视频: {video_file.name}")
    logger.info(f"文件大小: {video_file.stat().st_size / 1024 / 1024:.2f} MB")

    # 导入 VideoParser
    from app.services.parsers.video_parser import VideoParser
    from app.services.parsers.factory import ParserFactory

    # 初始化 VideoParser
    logger.info("\n[1/3] 初始化 VideoParser...")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("未设置 DASHSCOPE_API_KEY，部分功能将被跳过")

    parser = VideoParser(
        output_dir="media/extracted",
        interval_seconds=2,  # 每2秒读取一帧
        api_key=api_key
    )
    logger.info(f"  采样间隔: {parser.interval_seconds} 秒")

    # 解析视频
    logger.info("\n[2/3] 解析视频（关键帧提取 + 视觉理解 + ASR）...")
    start_time = datetime.now()
    result = await parser.parse(video_file)
    parse_duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"解析完成，耗时: {parse_duration:.2f}秒")
    logger.info(f"  文本块数: {len(result.chunks)}")
    logger.info(f"  关键帧图片数: {len(result.images)}")

    # 统计不同类型的文本块
    type_counts = {}
    for chunk in result.chunks:
        chunk_type = chunk.metadata.get("type", "unknown")
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

    logger.info(f"  类型分布: {type_counts}")

    # 显示解析结果详情
    logger.info("\n" + "=" * 60)
    logger.info("解析结果详情:")
    logger.info("=" * 60)

    for i, chunk in enumerate(result.chunks):
        metadata = chunk.metadata
        chunk_type = metadata.get("type", "unknown")
        logger.info(f"\n--- 文本块 {i+1} [{chunk_type}] ---")

        # 显示元数据
        if chunk_type == "visual":
            logger.info(f"  时间戳: {metadata.get('timestamp')}秒")
            logger.info(f"  帧号: {metadata.get('frame_number')}")
        elif chunk_type == "audio":
            logger.info(f"  开始时间: {metadata.get('start_time'):.2f}s")
            logger.info(f"  结束时间: {metadata.get('end_time'):.2f}s")

        # 显示内容
        content = chunk.content
        if len(content) > 150:
            logger.info(f"  内容: {content[:150]}...")
        else:
            logger.info(f"  内容: {content}")

    # 使用 ParserFactory 测试
    logger.info("\n[3/3] 使用 ParserFactory 测试...")
    result2 = await ParserFactory.parse_file(video_file)
    logger.info(f"  ParserFactory 解析: {len(result2.chunks)} 个文本块")

    logger.info("\n" + "=" * 60)
    logger.info("VideoParser 测试完成")
    logger.info("=" * 60)


async def test_vision_service():
    """
    单独测试 VisionService 视觉理解服务
    """
    logger.info("=" * 60)
    logger.info("测试 VisionService 视觉理解服务")
    logger.info("=" * 60)

    from app.services.ai.vision_service import VisionService

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("未设置 DASHSCOPE_API_KEY")
        return

    service = VisionService(api_key=api_key)
    logger.info(f"  使用模型: {service.model}")

    logger.info("\n测试通过图片路径调用（需要提供真实图片路径）...")
    # 注意: 这里需要真实的图片路径才能测试

    logger.info("\n" + "=" * 60)
    logger.info("VisionService 测试说明完成")
    logger.info("=" * 60)


def print_usage():
    """打印使用说明"""
    print("""
多模态解析测试

用法:
    python -m tests.test_multimodal_parser <命令> [参数]

命令:
    image <图片路径>     测试图片解析
    video <视频路径>    测试视频解析（带视觉理解）
    vision              测试视觉理解服务

示例:
    # 测试图片解析
    python -m tests.test_multimodal_parser image ./test.jpg

    # 测试视频解析
    python -m tests.test_multimodal_parser video ./test.mp4

    # 测试视觉服务
    python -m tests.test_multimodal_parser vision
""")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "image":
        if len(sys.argv) < 3:
            image_path = os.getenv("TEST_IMAGE_PATH")
            if not image_path:
                print("错误: 请提供图片路径")
                print("用法: python -m tests.test_multimodal_parser image <图片路径>")
                sys.exit(1)
        else:
            image_path = sys.argv[2]

        asyncio.run(test_image_parser(image_path))

    elif command == "video":
        if len(sys.argv) < 3:
            video_path = os.getenv("TEST_VIDEO_PATH")
            if not video_path:
                print("错误: 请提供视频路径")
                print("用法: python -m tests.test_multimodal_parser video <视频路径>")
                sys.exit(1)
        else:
            video_path = sys.argv[2]

        asyncio.run(test_video_parser_with_vision(video_path))

    elif command == "vision":
        asyncio.run(test_vision_service())

    else:
        print(f"未知命令: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
