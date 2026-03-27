"""add tags and updated_at to knowledge_libraries

Revision ID: add_lib_tags_001
Revises: question_papers_001
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_lib_tags_001'
down_revision = 'question_papers_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('knowledge_libraries',
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]')
    )
    op.add_column('knowledge_libraries',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Backfill updated_at from created_at
    op.execute("UPDATE knowledge_libraries SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column('knowledge_libraries', 'updated_at', nullable=False)


def downgrade() -> None:
    op.drop_column('knowledge_libraries', 'updated_at')
    op.drop_column('knowledge_libraries', 'tags')
