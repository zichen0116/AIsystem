"""add ppt tables

Revision ID: add_ppt_tables_001
Revises: 1b6dd46c3766
Create Date: 2026-03-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_ppt_tables_001'
down_revision: Union[str, None] = '1b6dd46c3766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ppt_sessions
    op.create_table(
        'ppt_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_outline_id', sa.Integer(), nullable=True),
        sa.Column('current_result_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ppt_sessions_user_id', 'ppt_sessions', ['user_id'])

    # ppt_outlines
    op.create_table(
        'ppt_outlines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('image_urls', postgresql.JSONB(), nullable=True),
        sa.Column('template_id', sa.String(length=100), nullable=True),
        sa.Column('knowledge_library_ids', postgresql.JSONB(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['ppt_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ppt_outlines_session_id', 'ppt_outlines', ['session_id'])

    # ppt_messages
    op.create_table(
        'ppt_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['ppt_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ppt_messages_session_id', 'ppt_messages', ['session_id'])

    # ppt_results
    op.create_table(
        'ppt_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('outline_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('template_id', sa.String(length=100), nullable=True),
        sa.Column('docmee_ppt_id', sa.String(length=200), nullable=True),
        sa.Column('source_pptx_property', sa.Text(), nullable=True),
        sa.Column('edited_pptx_property', sa.Text(), nullable=True),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_page', sa.Integer(), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['ppt_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outline_id'], ['ppt_outlines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ppt_results_session_id', 'ppt_results', ['session_id'])

    # 添加ppt_sessions的外键（延迟创建，因为依赖ppt_outlines和ppt_results）
    op.create_foreign_key(
        'fk_ppt_sessions_current_outline',
        'ppt_sessions', 'ppt_outlines',
        ['current_outline_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_ppt_sessions_current_result',
        'ppt_sessions', 'ppt_results',
        ['current_result_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_ppt_sessions_current_result', 'ppt_sessions', type_='foreignkey')
    op.drop_constraint('fk_ppt_sessions_current_outline', 'ppt_sessions', type_='foreignkey')
    op.drop_table('ppt_results')
    op.drop_table('ppt_messages')
    op.drop_table('ppt_outlines')
    op.drop_table('ppt_sessions')
