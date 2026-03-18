"""
教案删除 API 测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson_plan import LessonPlan
from app.models.chat_history import ChatHistory


@pytest.mark.asyncio
async def test_delete_lesson_plan_success(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user_id: int
):
    """测试删除教案成功"""
    # 创建教案
    plan = LessonPlan(user_id=test_user_id, title="测试教案", content="内容", status="draft")
    db_session.add(plan)
    await db_session.flush()

    # 创建关联的对话历史
    msg = ChatHistory(session_id=plan.session_id, user_id=test_user_id, role="user", content="测试")
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_id = plan.id
    session_id = plan.session_id

    # 删除教案
    response = await client.delete(f"/api/v1/lesson-plan/{plan_id}", headers=auth_headers)
    assert response.status_code == 204

    # 验证教案已删除
    from sqlalchemy import select
    result = await db_session.execute(select(LessonPlan).where(LessonPlan.id == plan_id))
    assert result.scalar_one_or_none() is None

    # 验证对话历史已级联删除
    result = await db_session.execute(
        select(ChatHistory).where(ChatHistory.session_id == session_id)
    )
    assert result.scalar_one_or_none() is None
