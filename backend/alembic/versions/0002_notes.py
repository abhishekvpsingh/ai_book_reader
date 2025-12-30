"""add notes

Revision ID: 0002_notes
Revises: 0001_initial
Create Date: 2024-12-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_notes"

down_revision = "0001_initial"

branch_labels = None

depends_on = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("page_num", sa.Integer(), nullable=False),
        sa.Column("selection_text", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("rects_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_notes_book_id", "notes", ["book_id"])
    op.create_index("ix_notes_section_id", "notes", ["section_id"])
    op.create_index("ix_notes_page_num", "notes", ["page_num"])


def downgrade() -> None:
    op.drop_table("notes")
