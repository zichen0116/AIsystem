"""add ppt project intents table

Revision ID: add_ppt_project_intents_001
Revises: 86c4f56b734d
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_ppt_project_intents_001"
down_revision: Union[str, None] = "86c4f56b734d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ppt_project_intents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("duration", sa.Text(), nullable=True),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column("style", sa.Text(), nullable=True),
        sa.Column("interaction", sa.Text(), nullable=True),
        sa.Column("extra", sa.Text(), nullable=True),
        sa.Column("confirmed_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pending_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score_goal", sa.Integer(), nullable=False),
        sa.Column("score_audience", sa.Integer(), nullable=False),
        sa.Column("score_structure", sa.Integer(), nullable=False),
        sa.Column("score_interaction", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("clarification_round", sa.Integer(), nullable=False),
        sa.Column("last_source_session_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["last_source_session_id"], ["ppt_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["ppt_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_ppt_project_intents_project_id"),
    )
    op.create_index("ix_ppt_project_intents_user_id", "ppt_project_intents", ["user_id"], unique=False)

    op.execute(
        """
        INSERT INTO ppt_project_intents (
            project_id,
            user_id,
            topic,
            confirmed_points,
            pending_items,
            score_goal,
            score_audience,
            score_structure,
            score_interaction,
            confidence,
            summary_text,
            status,
            clarification_round,
            created_at,
            updated_at
        )
        SELECT
            p.id,
            p.user_id,
            NULLIF(TRIM(COALESCE(p.theme, p.outline_text, '')), ''),
            '[]'::jsonb,
            '[]'::jsonb,
            35,
            35,
            35,
            35,
            35,
            '继续澄清中',
            'CLARIFYING',
            0,
            NOW(),
            NOW()
        FROM ppt_projects p
        WHERE NOT EXISTS (
            SELECT 1 FROM ppt_project_intents i WHERE i.project_id = p.id
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ppt_project_intents_user_id", table_name="ppt_project_intents")
    op.drop_table("ppt_project_intents")
