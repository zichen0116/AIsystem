"""
数据库初始化脚本
生成建表 SQL 语句并保存到 schema.sql
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, inspect
from app.core.database import Base
from app.models import *  # 导入所有模型


def generate_schema():
    """生成建表 SQL"""
    # 使用同步引擎生成 SQL
    DATABASE_URL_SYNC = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:postgres@localhost:5432/ai_teaching"
    )

    engine = create_engine(DATABASE_URL_SYNC)

    # 获取建表 SQL
    with engine.connect() as conn:
        sql_statements = []

        # 为每个模型生成 CREATE TABLE 语句
        for table_name, table in Base.metadata.tables.items():
            # 生成创建表语句
            create_stmt = str(table.compile(dialect=engine.dialect))
            sql_statements.append(create_stmt + ";")

        # 写入文件
        output_path = Path(__file__).parent.parent / "schema.sql"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("-- 多模态 AI 互动式教学智能体 数据库表结构\n")
            f.write(f"-- 生成时间: {__import__('datetime').datetime.now()}\n\n")

            for sql in sql_statements:
                f.write(sql + "\n\n")

        print(f"建表 SQL 已生成: {output_path}")

    # 同时打印到控制台
    print("\n" + "=" * 50)
    print("建表 SQL 语句:")
    print("=" * 50)
    for sql in sql_statements:
        print(sql)
        print()


if __name__ == "__main__":
    generate_schema()
