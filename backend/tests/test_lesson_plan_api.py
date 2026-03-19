"""
教案API端点测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson_plan import LessonPlan
from app.models.chat_history import ChatHistory


@pytest.mark.asyncio
async def test_list_lesson_plans_empty(client: AsyncClient, auth_headers: dict):
    """测试空列表"""
    response = await client.get("/api/v1/lesson-plan/list", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_lesson_plans_with_data(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user_id: int
):
    """测试有数据的列表"""
    # 创建测试数据
    plan1 = LessonPlan(user_id=test_user_id, title="教案1", content="内容1", status="draft")
    plan2 = LessonPlan(user_id=test_user_id, title="教案2", content="内容2", status="completed")
    db_session.add_all([plan1, plan2])
    await db_session.commit()

    response = await client.get("/api/v1/lesson-plan/list", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] in ["教案1", "教案2"]


@pytest.mark.asyncio
async def test_get_lesson_plan_detail_success(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user_id: int
):
    """测试获取教案详情成功"""
    plan = LessonPlan(user_id=test_user_id, title="测试教案", content="测试内容", status="draft")
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    response = await client.get(f"/api/v1/lesson-plan/{plan.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == plan.id
    assert data["title"] == "测试教案"
    assert data["content"] == "测试内容"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_get_lesson_plan_detail_not_found(client: AsyncClient, auth_headers: dict):
    """测试获取不存在的教案"""
    response = await client.get("/api/v1/lesson-plan/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_lesson_plan_messages_success(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user_id: int
):
    """测试获取对话历史成功"""
    plan = LessonPlan(user_id=test_user_id, title="测试教案", content="内容", status="draft")
    db_session.add(plan)
    await db_session.flush()

    # 添加对话历史
    msg1 = ChatHistory(session_id=plan.session_id, user_id=test_user_id, role="user", content="你好")
    msg2 = ChatHistory(session_id=plan.session_id, user_id=test_user_id, role="assistant", content="你好！")
    db_session.add_all([msg1, msg2])
    await db_session.commit()
    await db_session.refresh(plan)

    response = await client.get(f"/api/v1/lesson-plan/{plan.id}/messages", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "你好"
    assert data["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_get_lesson_plan_messages_not_found(client: AsyncClient, auth_headers: dict):
    """测试获取不存在教案的对话历史"""
    response = await client.get("/api/v1/lesson-plan/99999/messages", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_lesson_plans_unauthorized(client: AsyncClient):
    """测试未授权访问"""
    response = await client.get("/api/v1/lesson-plan/list")
    assert response.status_code == 401
