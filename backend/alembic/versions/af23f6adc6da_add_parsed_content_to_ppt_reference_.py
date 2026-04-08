"""add parsed_content to ppt_reference_files

Revision ID: af23f6adc6da
Revises: add_renovation_fields_001
Create Date: 2026-04-07 23:37:20.574272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'af23f6adc6da'
down_revision: Union[str, None] = 'add_renovation_fields_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ppt_reference_files', sa.Column('parsed_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('ppt_reference_files', 'parsed_content')
