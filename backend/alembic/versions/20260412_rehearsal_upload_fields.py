"""add rehearsal upload fields

Revision ID: 20260412_rehearsal_upload_fields
Revises: 757e2778ff51
Create Date: 2026-04-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260412_rehearsal_upload_fields'
down_revision: Union[str, None] = '757e2778ff51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        'rehearsal_sessions',
        sa.Column('source', sa.String(length=20), nullable=False, server_default='topic'),
    )
    op.add_column('rehearsal_sessions', sa.Column('original_file_url', sa.Text(), nullable=True))
    op.add_column('rehearsal_sessions', sa.Column('original_file_name', sa.String(length=255), nullable=True))
    op.add_column('rehearsal_sessions', sa.Column('converted_pdf_url', sa.Text(), nullable=True))
    op.add_column('rehearsal_sessions', sa.Column('total_pages', sa.Integer(), nullable=True))

    op.add_column('rehearsal_scenes', sa.Column('original_page_number', sa.Integer(), nullable=True))
    op.add_column(
        'rehearsal_scenes',
        sa.Column('is_skipped', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column('rehearsal_scenes', sa.Column('skip_reason', sa.String(length=100), nullable=True))
    op.add_column('rehearsal_scenes', sa.Column('page_image_url', sa.Text(), nullable=True))
    op.add_column('rehearsal_scenes', sa.Column('page_text', sa.Text(), nullable=True))
    op.add_column('rehearsal_scenes', sa.Column('script_text', sa.Text(), nullable=True))
    op.add_column('rehearsal_scenes', sa.Column('audio_url', sa.Text(), nullable=True))



def downgrade() -> None:
    op.drop_column('rehearsal_scenes', 'audio_url')
    op.drop_column('rehearsal_scenes', 'script_text')
    op.drop_column('rehearsal_scenes', 'page_text')
    op.drop_column('rehearsal_scenes', 'page_image_url')
    op.drop_column('rehearsal_scenes', 'skip_reason')
    op.drop_column('rehearsal_scenes', 'is_skipped')
    op.drop_column('rehearsal_scenes', 'original_page_number')

    op.drop_column('rehearsal_sessions', 'total_pages')
    op.drop_column('rehearsal_sessions', 'converted_pdf_url')
    op.drop_column('rehearsal_sessions', 'original_file_name')
    op.drop_column('rehearsal_sessions', 'original_file_url')
    op.drop_column('rehearsal_sessions', 'source')
