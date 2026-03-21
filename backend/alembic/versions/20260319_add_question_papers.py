"""add question_papers table for saved generated exams

Revision ID: question_papers_001
Revises: 1b6dd46c3766
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "question_papers_001"
down_revision = "1b6dd46c3766"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_papers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_question_papers_user_id", "question_papers", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_question_papers_user_id", table_name="question_papers")
    op.drop_table("question_papers")
