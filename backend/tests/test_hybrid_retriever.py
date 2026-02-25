"""
混合检索测试脚本
测试向量检索 + BM25 混合搜索（使用阿里云 DashScope API）
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载 .env 配置
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env", override=True)

print(f"加载的 API Key: {os.getenv('DASHSCOPE_API_KEY', '未找到')[:15]}...")

from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.vector_store import VectorStore
from langchain_core.documents import Document


async def test_hybrid_retrieval():
    """测试混合检索"""
    
    print("=" * 60)
    print("混合检索测试开始 (阿里云 DashScope API)")
    print("=" * 60)
    
    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("错误: 未配置 DASHSCOPE_API_KEY")
        return
    print(f"API Key: {api_key[:10]}...")
    
    # 测试文档 - 模拟 PDF/Word 解析结果
    test_documents = [
        Document(
            page_content="Python 是一种高级编程语言，广泛应用于 Web 开发、数据分析和人工智能领域。",
            metadata={"source": "python_intro.pdf", "page": 1, "user_id": 1}
        ),
        Document(
            page_content="Java 是一种面向对象的编程语言，主要用于企业级应用开发和 Android 开发。",
            metadata={"source": "java_intro.pdf", "page": 1, "user_id": 1}
        ),
        Document(
            page_content="机器学习是人工智能的一个分支，通过算法让计算机从数据中学习。",
            metadata={"source": "ml_intro.pdf", "page": 2, "user_id": 1}
        ),
        Document(
            page_content="深度学习是机器学习的分支，使用神经网络模型进行特征学习和预测。",
            metadata={"source": "dl_intro.pdf", "page": 1, "user_id": 1}
        ),
        Document(
            page_content="Web 开发包括前端和后端技术，前端常用 HTML、CSS、JavaScript，后端可以用 Python、Java、Go 等。",
            metadata={"source": "web_dev.pdf", "page": 3, "user_id": 1}
        ),
        Document(
            page_content="数据分析使用 Python 的 Pandas、NumPy 库进行数据处理和可视化。",
            metadata={"source": "data_analysis.pdf", "page": 1, "user_id": 1}
        ),
    ]
    
    user_id = 1
    
    # 1. 初始化向量存储
    print("\n[1/4] 初始化向量存储...")
    vector_store = VectorStore(
        collection_name="test_hybrid",
        embedding_model="tongyi-embedding-vision-flash"
    )
    
    # 清空已有数据
    try:
        vector_store.vectorstore.delete(where={"user_id": user_id})
        print("  已清空用户旧数据")
    except Exception as e:
        print(f"  清空数据: {e}")
    
    # 2. 添加文档到向量库
    print("\n[2/4] 添加文档到向量库...")
    from app.services.parsers.base import ParsedChunk
    
    chunks = [
        ParsedChunk(content=doc.page_content, metadata=doc.metadata)
        for doc in test_documents
    ]
    vector_store.add_documents(chunks, user_id=user_id)
    print(f"  已添加 {len(chunks)} 个文档到向量库")
    
    # 3. 初始化混合检索器并构建 BM25 索引
    print("\n[3/4] 构建 BM25 索引...")
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_weight=0.5,
        fusion_method="rrf"
    )
    
    # 为文档生成 ID
    doc_ids = [f"doc_{i}" for i in range(len(test_documents))]
    for i, doc in enumerate(test_documents):
        doc.metadata["doc_id"] = doc_ids[i]
    
    hybrid_retriever.build_bm25_index(user_id, test_documents)
    print("  BM25 索引构建完成")
    
    # 4. 执行混合检索测试
    print("\n[4/4] 执行混合检索测试")
    print("-" * 60)
    
    test_queries = [
        "Python 编程",
        "机器学习 深度学习",
        "Web 开发",
    ]
    
    for query in test_queries:
        print(f"\n>>> 查询: {query}")
        print("-" * 40)
        
        # 向量检索
        vector_results = vector_store.similarity_search(
            query=query, user_id=user_id, k=3
        )
        print(f"[向量检索 Top 3]:")
        for i, doc in enumerate(vector_results):
            src = doc.metadata.get('source', 'unknown')
            pg = doc.metadata.get('page', '?')
            content = doc.page_content[:40]
            print(f"  {i+1}. [{src}] 页面 {pg} - {content}...")
        
        # BM25 检索
        bm25_results = hybrid_retriever.bm25_index.search(
            user_id=user_id, query=query, top_k=3
        )
        print(f"\n[BM25 检索 Top 3]:")
        for i, (doc, score) in enumerate(bm25_results):
            src = doc.metadata.get('source', 'unknown')
            content = doc.page_content[:40]
            print(f"  {i+1}. [{src}] (得分: {score:.2f}) {content}...")
        
        # 混合检索
        hybrid_results = await hybrid_retriever.search(
            query=query, user_id=user_id, k=3
        )
        print(f"\n[混合检索 Top 3]:")
        for i, doc in enumerate(hybrid_results):
            src = doc.metadata.get('source', 'unknown')
            pg = doc.metadata.get('page', '?')
            content = doc.page_content[:40]
            print(f"  {i+1}. [{src}] 页面 {pg} - {content}...")
        
        print()
    
    print("=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    # 5. 测试不同融合方法
    print("\n\n融合方法对比测试")
    print("=" * 60)
    
    query = "Python 机器学习"
    
    # RRF 融合
    hybrid_rrf = HybridRetriever(vector_store=vector_store, bm25_weight=0.5, fusion_method="rrf")
    hybrid_rrf.build_bm25_index(user_id, test_documents)
    results_rrf = await hybrid_rrf.search(query=query, user_id=user_id, k=3)
    
    # 加权融合
    hybrid_weighted = HybridRetriever(vector_store=vector_store, bm25_weight=0.5, fusion_method="weighted")
    hybrid_weighted.build_bm25_index(user_id, test_documents)
    results_weighted = await hybrid_weighted.search(query=query, user_id=user_id, k=3)
    
    print(f"\n>>> 查询: {query}")
    print(f"\n[RRF 融合结果]:")
    for i, doc in enumerate(results_rrf):
        src = doc.metadata.get('source', 'unknown')
        print(f"  {i+1}. [{src}] {doc.page_content[:40]}...")
    
    print(f"\n[加权融合结果]:")
    for i, doc in enumerate(results_weighted):
        src = doc.metadata.get('source', 'unknown')
        print(f"  {i+1}. [{src}] {doc.page_content[:40]}...")


if __name__ == "__main__":
    asyncio.run(test_hybrid_retrieval())
