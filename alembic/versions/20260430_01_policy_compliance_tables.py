"""add policy compliance tables

Revision ID: 20260430_01
Revises: 20260427_02
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_01"
down_revision = "20260427_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_documents_status_deadline", "policy_documents", ["status", "deadline_at"])

    op.create_table(
        "policy_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delivery_channel", sa.String(length=16), nullable=False, server_default="BOTH"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SENT"),
        sa.Column("viewed_at", sa.DateTime(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("signed_file_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["policy_id"], ["policy_documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "user_id", name="uq_policy_recipients_policy_user"),
    )
    op.create_index("ix_policy_recipients_policy_status", "policy_recipients", ["policy_id", "status"])
    op.create_index("ix_policy_recipients_user_status", "policy_recipients", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_policy_recipients_user_status", table_name="policy_recipients")
    op.drop_index("ix_policy_recipients_policy_status", table_name="policy_recipients")
    op.drop_table("policy_recipients")
    op.drop_index("ix_policy_documents_status_deadline", table_name="policy_documents")
    op.drop_table("policy_documents")
