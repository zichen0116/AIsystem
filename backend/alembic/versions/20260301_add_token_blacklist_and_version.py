"""add token_blacklist table and token_version field

Revision ID: add_token_blacklist_001
Revises: add_knowledge_lib_001
Create Date: 2026-03-01

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_token_blacklist_001'
down_revision = 'add_knowledge_lib_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users 表添加 token_version 字段
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='1')
    )

    # 创建 token_blacklist 表
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expired_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_token_blacklist_token_hash', 'token_blacklist', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_token_blacklist_token_hash', table_name='token_blacklist')
    op.drop_table('token_blacklist')
    op.drop_column('users', 'token_version')
