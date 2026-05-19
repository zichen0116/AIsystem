# 仓库指南

## 项目结构与模块组织
本仓库是多模态 AI 教学平台的 FastAPI 后端。应用代码位于 `app/`：API 路由在 `app/api/`，配置和数据库初始化在 `app/core/`，SQLAlchemy 模型在 `app/models/`，请求/响应结构在 `app/schemas/`，业务逻辑在 `app/services/`，PPT 生成相关代码在 `app/generators/`。数据库迁移位于 `alembic/`。测试代码位于 `tests/`。运行时和生成资产位于 `media/`、`uploads/`、`logs/`、`chroma_data/`；不要将这些目录当作源码模块维护。

## 构建、测试与开发命令
安装依赖：

```powershell
pip install -r requirements.txt
```

本地运行 API：

```powershell
python run.py
```

启动完整开发环境，包括 Redis、PostgreSQL、FastAPI 和 Celery：

```powershell
python start_dev.py
```

运行全部测试：

```powershell
pytest tests -q
```

迭代时运行单个测试文件：

```powershell
pytest tests/test_lesson_plan_api.py -q
```

## 编码风格与命名约定
使用 Python 3.11+，遵循 PEP 8，并使用 4 空格缩进。公共函数和服务边界优先添加明确类型标注。模块和函数使用 `snake_case`，类以及 Pydantic/SQLAlchemy 模型使用 `PascalCase`，常量和环境变量键使用 `UPPER_SNAKE_CASE`。路由层保持轻量；业务规则放在 `app/services/`，持久化定义放在 `app/models/`。

## 测试指南
项目使用 `pytest`。新增测试放在 `tests/`，文件名使用 `test_*.py`，测试函数名应具备描述性，例如 `test_lesson_plan_delete_removes_references`。解析逻辑、提示词辅助函数和服务逻辑优先编写聚焦单元测试；修改路由行为时补充 API 测试。提交较大改动前，先运行相关单测，再运行 `pytest tests -q`。

## 提交与 Pull Request 指南
近期提交历史使用较短标题，并包含 `feat:`、`bugfix:`、`docs:` 等前缀。提交信息应简洁、使用祈使语气，例如 `feat: add rehearsal media cleanup` 或 `bugfix: handle empty PPT export`。Pull Request 应包含简短摘要、测试证据、可用时关联 issue 或任务；涉及用户可见 API 或生成资产变化时，附截图或样例输出。

## 安全与配置建议
本地密钥应放在 `.env`；保持 `.env.example` 安全且不包含敏感值。不要提交 API Key、生成媒体、上传文件、Chroma 数据、日志或数据库转储。新增配置时，在 `app/core/config.py` 中定义默认值，并在 `.env.example` 中记录必需环境变量。
