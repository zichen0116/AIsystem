"""add renovation fields to ppt_pages and ppt_projects

Revision ID: add_renovation_fields_001
Revises: add_ppt_project_intents_001
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_renovation_fields_001"
down_revision: Union[str, None] = "add_ppt_project_intents_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ppt_pages", sa.Column("renovation_status", sa.String(20), nullable=True))
    op.add_column("ppt_pages", sa.Column("renovation_error", sa.Text(), nullable=True))
    op.add_column("ppt_projects", sa.Column("description_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ppt_projects", "description_text")
    op.drop_column("ppt_pages", "renovation_error")
    op.drop_column("ppt_pages", "renovation_status")
