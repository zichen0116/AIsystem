"""
测试真实文件解析
测试 test1.pdf, test2.docx, test3.mp4
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from app.services.parsers.factory import ParserFactory


async def test_real_file(file_path: Path):
    """测试单个真实文件"""
    print(f"\n{'='*50}")
    print(f"测试文件: {file_path.name}")
    print(f"{'='*50}")
    
    if not file_path.exists():
        print(f"[SKIP] 文件不存在: {file_path}")
        return
    
    # 获取解析器
    parser = ParserFactory.get_parser(str(file_path))
    if not parser:
        print(f"[SKIP] 不支持的文件类型: {file_path.suffix}")
        return
    
    print(f"使用解析器: {parser.__class__.__name__}")
    
    try:
        # 解析文件
        result = await parser.parse(file_path)
        
        print(f"\n[OK] 解析成功!")
        print(f"  - 文本块数: {len(result.chunks)}")
        print(f"  - 图片数: {len(result.images)}")
        
        # 显示文本内容预览
        if result.chunks:
            print(f"\n文本内容预览:")
            for i, chunk in enumerate(result.chunks[:3]):  # 只显示前3个块
                content = chunk.content[:200].replace('\n', ' ')
                print(f"  块 {i+1}: {content}...")
                print(f"    元数据: {chunk.metadata}")
        
        # 显示提取的图片
        if result.images:
            print(f"\n提取的图片:")
            for i, img in enumerate(result.images[:5]):  # 只显示前5张
                print(f"  图片 {i+1}: {img}")
        
        return result
        
    except Exception as e:
        print(f"[FAIL] 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_vector_store_with_real_docs():
    """将真实文件添加到向量存储"""
    print(f"\n{'='*50}")
    print("测试向量存储（真实文件）")
    print(f"{'='*50}")
    
    from app.services.rag.vector_store import VectorStore
    
    media_dir = Path("media/extracted")
    
    # 收集所有文件的 chunks
    all_chunks = []
    
    for file_path in [media_dir / "test1.pdf", media_dir / "test2.docx"]:
        if not file_path.exists():
            continue
            
        parser = ParserFactory.get_parser(str(file_path))
        if not parser:
            continue
            
        print(f"\n解析: {file_path.name}")
        result = await parser.parse(file_path)
        
        if result.chunks:
            all_chunks.extend(result.chunks)
            print(f"  提取了 {len(result.chunks)} 个文本块")
    
    if not all_chunks:
        print("[SKIP] 没有可添加的文本块")
        return
    
    # 添加到向量库
    print(f"\n添加 {len(all_chunks)} 个文本块到向量库...")
    vs = VectorStore(collection_name="real_files_test")
    count = vs.add_documents(all_chunks, user_id=1)
    print(f"[OK] 成功添加 {count} 个文档")
    
    # 搜索测试
    print("\n搜索测试:")
    queries = ["Python", "教学", "学习目标", "课程"]
    for query in queries:
        results = vs.similarity_search(query, user_id=1, k=2)
        if results:
            print(f"\n  查询 '{query}':")
            for i, doc in enumerate(results):
                preview = doc.page_content[:80].replace('\n', ' ')
                print(f"    {i+1}. {preview}... (来源: {doc.metadata.get('source', 'unknown')})")
    
    # 显示集合信息
    info = vs.get_collection_info()
    print(f"\n向量库信息: {info}")


async def main():
    """主函数"""
    print("="*50)
    print("真实文件解析测试")
    print("="*50)
    
    media_dir = Path("media/extracted")
    
    # 测试各个文件
    files = ["test1.pdf", "test2.docx", "test3.mp4"]
    
    for filename in files:
        file_path = media_dir / filename
        await test_real_file(file_path)
    
    # 测试向量存储
    await test_vector_store_with_real_docs()
    
    print("\n" + "="*50)
    print("测试完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
