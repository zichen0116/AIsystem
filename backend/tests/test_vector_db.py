"""
向量数据库测试脚本
测试 ChromaDB 向量存储功能
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def test_chroma_directly():
    """直接测试 ChromaDB（不通过 LangChain）"""
    print("\n" + "=" * 50)
    print("测试: ChromaDB 直接连接")
    print("=" * 50)
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # 创建客户端
        client = chromadb.PersistentClient(
            path="chroma_data_test",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 创建或获取集合
        collection = client.get_or_create_collection(
            name="test_collection",
            metadata={"hnsw:space": "cosine"}
        )
        
        # 添加测试文档
        collection.add(
            documents=[
                "Python 是一种广泛使用的解释型、高级和通用的编程语言。",
                "机器学习是人工智能的一个分支，专门研究计算机怎样模拟或实现人类的学习行为。",
                "深度学习是机器学习的分支，是一种以人工神经网络为架构，对数据进行表征学习的算法。"
            ],
            ids=["doc1", "doc2", "doc3"],
            metadatas=[
                {"source": "test.txt", "page": 1, "user_id": 1},
                {"source": "test.txt", "page": 2, "user_id": 1},
                {"source": "test.txt", "page": 3, "user_id": 1}
            ]
        )
        
        print(f"✓ 成功添加 3 个文档到集合")
        
        # 查询
        results = collection.query(
            query_texts=["Python编程"],
            n_results=2,
            where={"user_id": 1}
        )
        
        print(f"\n查询 'Python编程' 结果:")
        for i, (doc, distance) in enumerate(zip(results['documents'][0], results['distances'][0])):
            print(f"  {i+1}. {doc[:50]}... (距离: {distance:.4f})")
        
        # 获取集合信息
        count = collection.count()
        print(f"\n集合中的文档数: {count}")
        
        # 清理
        client.delete_collection("test_collection")
        print("✓ 测试完成，已清理测试集合")
        
        return True
        
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("  请运行: pip install chromadb")
        return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store_service():
    """测试 VectorStore 服务"""
    print("\n" + "=" * 50)
    print("测试: VectorStore 服务 (使用阿里云百炼 Embedding)")
    print("=" * 50)
    
    try:
        from app.services.rag.vector_store import VectorStore
        from app.services.parsers.base import ParsedChunk
        
        # 初始化向量存储（默认使用阿里云百炼）
        vs = VectorStore(collection_name="test_service_collection")
        
        # 添加测试文档
        chunks = [
            ParsedChunk(
                content="Python 是一种广泛使用的解释型、高级和通用的编程语言。",
                metadata={"source": "test.txt", "page": 1}
            ),
            ParsedChunk(
                content="机器学习是人工智能的一个分支，专门研究计算机怎样模拟或实现人类的学习行为。",
                metadata={"source": "test.txt", "page": 2}
            ),
            ParsedChunk(
                content="深度学习是机器学习的分支，是一种以人工神经网络为架构，对数据进行表征学习的算法。",
                metadata={"source": "test.txt", "page": 3}
            ),
        ]
        
        print(f"添加 {len(chunks)} 个文档到向量库...")
        count = vs.add_documents(chunks, user_id=1)
        print(f"✓ 成功添加 {count} 个文档")
        
        # 搜索测试
        print("\n搜索: 'Python编程'")
        results = vs.similarity_search("Python编程", user_id=1, k=2)
        
        print(f"找到 {len(results)} 个结果:")
        for i, doc in enumerate(results):
            print(f"\n  结果 {i + 1}:")
            print(f"    内容: {doc.page_content[:80]}...")
            print(f"    元数据: {doc.metadata}")
        
        # 获取集合信息
        info = vs.get_collection_info()
        print(f"\n向量库信息: {info}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("  可能需要安装: pip install langchain langchain-chroma")
        return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("向量数据库测试")
    print("=" * 50)
    
    # 测试 1: 直接测试 ChromaDB
    result1 = test_chroma_directly()
    
    # 测试 2: 测试 VectorStore 服务（如果依赖已安装）
    result2 = test_vector_store_service()
    
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    print(f"ChromaDB 直接连接: {'✓ 通过' if result1 else '✗ 失败'}")
    print(f"VectorStore 服务: {'✓ 通过' if result2 else '✗ 失败'}")
    
    if result1 or result2:
        print("\n向量数据库功能正常！")
    else:
        print("\n请检查依赖安装:")
        print("  pip install chromadb langchain langchain-chroma")


if __name__ == "__main__":
    main()
