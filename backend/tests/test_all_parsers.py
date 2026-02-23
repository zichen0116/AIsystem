"""
多模态解析完整测试
测试 PDF/Word/图片/视频 四种文件类型的解析
"""
import asyncio
import os
import sys
import json
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


async def test_pdf_parser(file_path: str):
    """测试 PDF 解析器"""
    logger.info("=" * 60)
    logger.info("测试 PDF 解析器")
    logger.info("=" * 60)

    pdf_file = Path(file_path)
    if not pdf_file.exists():
        logger.error(f"PDF 文件不存在: {file_path}")
        return

    logger.info(f"测试文件: {pdf_file.name}")
    logger.info(f"文件大小: {pdf_file.stat().st_size / 1024:.2f} KB")

    from app.services.parsers.factory import ParserFactory

    # 使用 ParserFactory（统一接口）
    logger.info("\n使用 ParserFactory 解析...")
    start_time = datetime.now()
    result = await ParserFactory.parse_file(pdf_file)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"解析完成，耗时: {duration:.2f}秒")
    logger.info(f"  文本块数: {len(result.chunks)}")
    logger.info(f"  图片数: {len(result.images)}")

    # 统计
    for i, chunk in enumerate(result.chunks):
        metadata = chunk.metadata
        has_image = metadata.get("has_image", False)
        image_count = metadata.get("image_count", 0)
        logger.info(f"\n--- 文本块 {i+1} ---")
        logger.info(f"  页码: {metadata.get('page')}")
        logger.info(f"  类型: {metadata.get('type')}")
        logger.info(f"  含图片: {has_image} ({image_count}张)")
        content = chunk.content
        logger.info(f"  内容: {content}")

    # 保存结果为 JSON 文件
    save_json_result(pdf_file.stem, result)

    logger.info("\n" + "=" * 60)
    logger.info("PDF 解析测试完成")
    logger.info("=" * 60)


async def test_word_parser(file_path: str):
    """测试 Word 解析器"""
    logger.info("=" * 60)
    logger.info("测试 Word 解析器")
    logger.info("=" * 60)

    doc_file = Path(file_path)
    if not doc_file.exists():
        logger.error(f"Word 文件不存在: {file_path}")
        return

    logger.info(f"测试文件: {doc_file.name}")
    logger.info(f"文件大小: {doc_file.stat().st_size / 1024:.2f} KB")

    from app.services.parsers.factory import ParserFactory

    # 使用 ParserFactory（统一接口）
    logger.info("\n使用 ParserFactory 解析...")
    start_time = datetime.now()
    result = await ParserFactory.parse_file(doc_file)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"解析完成，耗时: {duration:.2f}秒")
    logger.info(f"  文本块数: {len(result.chunks)}")
    logger.info(f"  图片数: {len(result.images)}")

    # 统计
    for i, chunk in enumerate(result.chunks):
        metadata = chunk.metadata
        has_image = metadata.get("has_image", False)
        image_count = metadata.get("image_count", 0)
        logger.info(f"\n--- 文本块 {i+1} ---")
        logger.info(f"  页码: {metadata.get('page')}")
        logger.info(f"  类型: {metadata.get('type')}")
        logger.info(f"  含图片: {has_image} ({image_count}张)")
        content = chunk.content
        logger.info(f"  内容: {content}")

    # 保存结果为 JSON 文件
    save_json_result(doc_file.stem, result)

    logger.info("\n" + "=" * 60)
    logger.info("Word 解析测试完成")
    logger.info("=" * 60)


async def test_image_parser(file_path: str):
    """测试图片解析器"""
    logger.info("=" * 60)
    logger.info("测试图片解析器")
    logger.info("=" * 60)

    image_file = Path(file_path)
    if not image_file.exists():
        logger.error(f"图片文件不存在: {file_path}")
        return

    logger.info(f"测试文件: {image_file.name}")
    logger.info(f"文件大小: {image_file.stat().st_size / 1024:.2f} KB")

    from app.services.parsers.factory import ParserFactory

    # 使用 ParserFactory（统一接口）
    logger.info("\n使用 ParserFactory 解析...")
    start_time = datetime.now()
    result = await ParserFactory.parse_file(image_file)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"解析完成，耗时: {duration:.2f}秒")
    logger.info(f"  文本块数: {len(result.chunks)}")
    logger.info(f"  图片数: {len(result.images)}")

    for i, chunk in enumerate(result.chunks):
        metadata = chunk.metadata
        logger.info(f"\n--- 文本块 {i+1} ---")
        logger.info(f"  来源: {metadata.get('source')}")
        logger.info(f"  类型: {metadata.get('type')}")
        content = chunk.content
        logger.info(f"  内容: {content}")

    # 保存结果为 JSON 文件
    save_json_result(image_file.stem, result)

    logger.info("\n" + "=" * 60)
    logger.info("图片解析测试完成")
    logger.info("=" * 60)


async def test_video_parser(file_path: str):
    """测试视频解析器"""
    logger.info("=" * 60)
    logger.info("测试视频解析器（视觉理解 + 感知哈希去重）")
    logger.info("=" * 60)

    video_file = Path(file_path)
    if not video_file.exists():
        logger.error(f"视频文件不存在: {file_path}")
        return

    logger.info(f"测试文件: {video_file.name}")
    logger.info(f"文件大小: {video_file.stat().st_size / 1024 / 1024:.2f} MB")

    from app.services.parsers.factory import ParserFactory

    # 使用 ParserFactory（统一接口）
    logger.info("\n使用 ParserFactory 解析...")
    start_time = datetime.now()
    result = await ParserFactory.parse_file(video_file)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"解析完成，耗时: {duration:.2f}秒")
    logger.info(f"  文本块数: {len(result.chunks)}")
    logger.info(f"  关键帧数: {len(result.images)}")

    # 统计不同类型
    type_counts = {}
    for chunk in result.chunks:
        chunk_type = chunk.metadata.get("type", "unknown")
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
    logger.info(f"  类型分布: {type_counts}")

    # 显示前3个文本块
    for i, chunk in enumerate(result.chunks[:3]):
        metadata = chunk.metadata
        chunk_type = metadata.get("type", "unknown")
        logger.info(f"\n--- 文本块 {i+1} [{chunk_type}] ---")

        if chunk_type == "visual":
            logger.info(f"  时间戳: {metadata.get('timestamp')}秒")
        elif chunk_type == "audio":
            logger.info(f"  开始时间: {metadata.get('start_time'):.2f}s")

        content = chunk.content
        logger.info(f"  内容: {content}")

    logger.info("\n" + "=" * 60)
    logger.info("视频解析测试完成")
    logger.info("=" * 60)

    # 保存结果为 JSON 文件
    save_json_result(video_file.stem, result)


def save_json_result(file_name: str, result):
    """保存解析结果为 JSON 文件"""
    output_dir = Path("media/parse_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{file_name}_result.json"

    data = {
        "chunks": [
            {
                "content": chunk.content,
                "metadata": chunk.metadata
            }
            for chunk in result.chunks
        ],
        "images": result.images
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"结果已保存到: {output_path}")


def print_usage():
    """打印使用说明"""
    print("""
============================================================
多模态解析完整测试

用法:
    python -m tests.test_all_parsers <类型> <文件路径>

类型:
    pdf     - 测试 PDF 解析
    word    - 测试 Word 解析
    image   - 测试图片解析
    video   - 测试视频解析
    all     - 测试所有类型（需要设置对应环境变量）

示例:
    python -m tests.test_all_parsers pdf ./tests/test.pdf
    python -m tests.test_all_parsers word ./tests/test.docx
    python -m tests.test_all_parsers image ./tests/test.jpg
    python -m tests.test_all_parsers video ./tests/test.mp4

环境变量方式:
    export TEST_PDF_PATH=./tests/test.pdf
    export TEST_WORD_PATH=./tests/test.docx
    export TEST_IMAGE_PATH=./tests/test.jpg
    export TEST_VIDEO_PATH=./tests/test.mp4
    python -m tests.test_all_parsers all
============================================================
""")


async def test_all():
    """测试所有类型（从环境变量读取路径）"""
    logger.info("=" * 60)
    logger.info("测试所有文件类型")
    logger.info("=" * 60)

    pdf_path = os.getenv("TEST_PDF_PATH")
    word_path = os.getenv("TEST_WORD_PATH")
    image_path = os.getenv("TEST_IMAGE_PATH")
    video_path = os.getenv("TEST_VIDEO_PATH")

    if pdf_path:
        await test_pdf_parser(pdf_path)
    else:
        logger.warning("未设置 TEST_PDF_PATH，跳过 PDF 测试")

    if word_path:
        await test_word_parser(word_path)
    else:
        logger.warning("未设置 TEST_WORD_PATH，跳过 Word 测试")

    if image_path:
        await test_image_parser(image_path)
    else:
        logger.warning("未设置 TEST_IMAGE_PATH，跳过图片测试")

    if video_path:
        await test_video_parser(video_path)
    else:
        logger.warning("未设置 TEST_VIDEO_PATH，跳过视频测试")

    logger.info("\n" + "=" * 60)
    logger.info("全部测试完成")
    logger.info("=" * 60)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "all":
        asyncio.run(test_all())
        return

    if len(sys.argv) < 3:
        print("错误: 请提供文件路径")
        print_usage()
        sys.exit(1)

    file_path = sys.argv[2]

    if command == "pdf":
        asyncio.run(test_pdf_parser(file_path))
    elif command == "word":
        asyncio.run(test_word_parser(file_path))
    elif command == "image":
        asyncio.run(test_image_parser(file_path))
    elif command == "video":
        asyncio.run(test_video_parser(file_path))
    else:
        print(f"未知类型: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
