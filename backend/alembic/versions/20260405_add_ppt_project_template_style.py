"""add template_style to ppt_projects

Revision ID: add_ppt_template_style_001
Revises: add_ppt_schema_001
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_ppt_template_style_001"
down_revision: Union[str, None] = "add_ppt_schema_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ppt_projects", sa.Column("template_style", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE ppt_projects
        SET template_style = NULLIF(TRIM(settings->>'template_style'), '')
        WHERE template_style IS NULL
          AND settings IS NOT NULL
          AND settings ? 'template_style'
        """
    )


def downgrade() -> None:
    op.drop_column("ppt_projects", "template_style")
