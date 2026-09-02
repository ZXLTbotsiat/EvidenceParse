"""Create canonical documents, upload occurrences, and review audit events."""

from typing import Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_document_review"
down_revision: Optional[str] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("schema_name", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_fingerprint", "schema_name", name="uq_documents_fingerprint_schema"
        ),
    )
    op.create_index("ix_documents_content_fingerprint", "documents", ["content_fingerprint"])
    op.create_index(
        "ix_documents_review_status_created", "documents", ["review_status", "created_at"]
    )
    op.create_table(
        "document_uploads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_uploads_document_id", "document_uploads", ["document_id"])
    op.create_table(
        "review_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("field_path", sa.String(length=256), nullable=True),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewer", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_events_document_id", "review_events", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_review_events_document_id", table_name="review_events")
    op.drop_table("review_events")
    op.drop_index("ix_document_uploads_document_id", table_name="document_uploads")
    op.drop_table("document_uploads")
    op.drop_index("ix_documents_review_status_created", table_name="documents")
    op.drop_index("ix_documents_content_fingerprint", table_name="documents")
    op.drop_table("documents")
