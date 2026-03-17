"""add cascade delete for chat_history

Revision ID: 69a613489351
Revises: 1b6dd46c3766
Create Date: 2026-03-18 00:31:14.258542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69a613489351'
down_revision: Union[str, None] = '1b6dd46c3766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 清理孤儿消息（session_id 在 lesson_plans 中不存在的记录）
    op.execute("""
        DELETE FROM chat_history
        WHERE NOT EXISTS (
            SELECT 1 FROM lesson_plans
            WHERE lesson_plans.session_id = chat_history.session_id
        )
    """)

    # 2. 添加外键约束，支持级联删除
    op.create_foreign_key(
        'fk_chat_history_session_id',
        'chat_history',
        'lesson_plans',
        ['session_id'],
        ['session_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 移除外键约束
    op.drop_constraint(
        'fk_chat_history_session_id',
        'chat_history',
        type_='foreignkey'
    )
