"""add knowledge_library, is_admin, library_id, vector_status_string

Revision ID: add_knowledge_lib_001
Revises: 
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_knowledge_lib_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 knowledge_libraries 表
    op.create_table(
        'knowledge_libraries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_libraries_owner_id', 'knowledge_libraries', ['owner_id'])
    op.create_index('ix_knowledge_libraries_is_deleted', 'knowledge_libraries', ['is_deleted'])

    # users 表添加 is_admin
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))

    # knowledge_assets 表添加 library_id
    op.add_column('knowledge_assets', sa.Column('library_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_knowledge_assets_library_id',
        'knowledge_assets', 'knowledge_libraries',
        ['library_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_knowledge_assets_library_id', 'knowledge_assets', ['library_id'])

    # vector_status 从 bool 改为 varchar
    op.alter_column(
        'knowledge_assets', 'vector_status',
        existing_type=sa.Boolean(),
        type_=sa.String(length=20),
        existing_nullable=False,
        postgresql_using="CASE WHEN vector_status THEN 'completed' ELSE 'pending' END"
    )
    op.alter_column('knowledge_assets', 'vector_status', server_default='pending')


def downgrade() -> None:
    op.drop_index('ix_knowledge_assets_library_id', table_name='knowledge_assets')
    op.drop_constraint('fk_knowledge_assets_library_id', 'knowledge_assets', type_='foreignkey')
    op.drop_column('knowledge_assets', 'library_id')
    op.alter_column(
        'knowledge_assets', 'vector_status',
        existing_type=sa.String(length=20),
        type_=sa.Boolean(),
        existing_nullable=False,
        postgresql_using="CASE WHEN vector_status = 'completed' THEN true ELSE false END"
    )
    op.drop_column('users', 'is_admin')
    op.drop_index('ix_knowledge_libraries_is_deleted', table_name='knowledge_libraries')
    op.drop_index('ix_knowledge_libraries_owner_id', table_name='knowledge_libraries')
    op.drop_table('knowledge_libraries')
