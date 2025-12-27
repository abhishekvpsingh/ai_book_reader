"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2024-07-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"

down_revision = None

branch_labels = None

depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
    )
    op.create_index("ix_sections_book_id", "sections", ["book_id"])
    op.create_index("ix_sections_parent_id", "sections", ["parent_id"])

    op.create_table(
        "section_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("page_num", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("caption", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_section_assets_book_id", "section_assets", ["book_id"])
    op.create_index("ix_section_assets_section_id", "section_assets", ["section_id"])

    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_summaries_section_id", "summaries", ["section_id"])

    op.create_table(
        "summary_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("summary_id", sa.Integer(), sa.ForeignKey("summaries.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_summary_versions_summary_id", "summary_versions", ["summary_id"])

    op.create_table(
        "audio_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("summary_versions.id"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audio_assets_version_id", "audio_assets", ["version_id"])
    op.create_index("ix_audio_assets_content_hash", "audio_assets", ["content_hash"])

    op.create_table(
        "reading_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("last_page", sa.Integer(), nullable=False),
        sa.Column("last_section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reading_progress_book_id", "reading_progress", ["book_id"], unique=True)


def downgrade() -> None:
    op.drop_table("reading_progress")
    op.drop_table("audio_assets")
    op.drop_table("summary_versions")
    op.drop_table("summaries")
    op.drop_table("section_assets")
    op.drop_table("sections")
    op.drop_table("books")
