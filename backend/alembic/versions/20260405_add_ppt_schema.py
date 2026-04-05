"""add ppt schema tables and courseware linkage

Revision ID: add_ppt_schema_001
Revises: f258ec926a55
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_ppt_schema_001"
down_revision: Union[str, None] = "f258ec926a55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ppt_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("creation_type", sa.String(length=20), nullable=False),
        sa.Column("outline_text", sa.Text(), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("theme", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("exported_file_url", sa.String(length=500), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("knowledge_library_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_projects_user_id", "ppt_projects", ["user_id"], unique=False)

    op.create_table(
        "ppt_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("image_version", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description_mode", sa.String(length=20), nullable=False),
        sa.Column("is_description_generating", sa.Boolean(), nullable=False),
        sa.Column("is_image_generating", sa.Boolean(), nullable=False),
        sa.Column("material_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["ppt_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_pages_project_id", "ppt_pages", ["project_id"], unique=False)

    op.create_table(
        "ppt_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["ppt_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["ppt_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_tasks_project_id", "ppt_tasks", ["project_id"], unique=False)
    op.create_index("ix_ppt_tasks_task_id", "ppt_tasks", ["task_id"], unique=True)

    op.create_table(
        "ppt_materials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("oss_path", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("material_type", sa.String(length=20), nullable=False),
        sa.Column("is_parsed", sa.Boolean(), nullable=False),
        sa.Column("parsed_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["ppt_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_materials_project_id", "ppt_materials", ["project_id"], unique=False)
    op.create_index("ix_ppt_materials_user_id", "ppt_materials", ["user_id"], unique=False)

    op.create_table(
        "ppt_reference_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("oss_path", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("parse_status", sa.String(length=20), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("parsed_outline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["ppt_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_reference_files_project_id", "ppt_reference_files", ["project_id"], unique=False)
    op.create_index("ix_ppt_reference_files_user_id", "ppt_reference_files", ["user_id"], unique=False)

    op.create_table(
        "ppt_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("session_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["ppt_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_sessions_project_id", "ppt_sessions", ["project_id"], unique=False)
    op.create_index("ix_ppt_sessions_user_id", "ppt_sessions", ["user_id"], unique=False)

    op.create_table(
        "ppt_user_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_user_templates_user_id", "ppt_user_templates", ["user_id"], unique=False)

    op.create_table(
        "ppt_page_image_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["ppt_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppt_page_image_versions_page_id", "ppt_page_image_versions", ["page_id"], unique=False)
    op.create_index("ix_ppt_page_image_versions_user_id", "ppt_page_image_versions", ["user_id"], unique=False)

    op.add_column("courseware", sa.Column("ppt_project_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_courseware_ppt_project_id",
        "courseware",
        "ppt_projects",
        ["ppt_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_courseware_ppt_project_id",
        "courseware",
        ["ppt_project_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_courseware_ppt_project_id", "courseware", type_="unique")
    op.drop_constraint("fk_courseware_ppt_project_id", "courseware", type_="foreignkey")
    op.drop_column("courseware", "ppt_project_id")

    op.drop_index("ix_ppt_page_image_versions_user_id", table_name="ppt_page_image_versions")
    op.drop_index("ix_ppt_page_image_versions_page_id", table_name="ppt_page_image_versions")
    op.drop_table("ppt_page_image_versions")

    op.drop_index("ix_ppt_user_templates_user_id", table_name="ppt_user_templates")
    op.drop_table("ppt_user_templates")

    op.drop_index("ix_ppt_sessions_user_id", table_name="ppt_sessions")
    op.drop_index("ix_ppt_sessions_project_id", table_name="ppt_sessions")
    op.drop_table("ppt_sessions")

    op.drop_index("ix_ppt_reference_files_user_id", table_name="ppt_reference_files")
    op.drop_index("ix_ppt_reference_files_project_id", table_name="ppt_reference_files")
    op.drop_table("ppt_reference_files")

    op.drop_index("ix_ppt_materials_user_id", table_name="ppt_materials")
    op.drop_index("ix_ppt_materials_project_id", table_name="ppt_materials")
    op.drop_table("ppt_materials")

    op.drop_index("ix_ppt_tasks_task_id", table_name="ppt_tasks")
    op.drop_index("ix_ppt_tasks_project_id", table_name="ppt_tasks")
    op.drop_table("ppt_tasks")

    op.drop_index("ix_ppt_pages_project_id", table_name="ppt_pages")
    op.drop_table("ppt_pages")

    op.drop_index("ix_ppt_projects_user_id", table_name="ppt_projects")
    op.drop_table("ppt_projects")