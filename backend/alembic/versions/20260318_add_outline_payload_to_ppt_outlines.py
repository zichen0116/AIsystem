"""add outline_payload to ppt_outlines

Revision ID: 20260318_add_outline_payload
Revises: add_ppt_tables_001
Create Date: 2026-03-18 23:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260318_add_outline_payload"
down_revision = "add_ppt_tables_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ppt_outlines",
        sa.Column(
            "outline_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ppt_outlines", "outline_payload")
