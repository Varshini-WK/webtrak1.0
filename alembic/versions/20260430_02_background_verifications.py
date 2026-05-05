"""add background verification table

Revision ID: 20260430_02
Revises: 20260430_01
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_02"
down_revision = "20260430_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("consent_form_signed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("identity", sa.String(length=100), nullable=True),
        sa.Column("employment_status", sa.String(length=20), nullable=False, server_default="NA"),
        sa.Column("reference_status", sa.String(length=20), nullable=False, server_default="NA"),
        sa.Column("mail_id_verified", sa.String(length=255), nullable=True),
        sa.Column("onboarding_form_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("overall_status", sa.String(length=20), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_background_verifications_user_id"),
    )
    op.create_index("ix_bgv_overall_status", "background_verifications", ["overall_status"])
    op.create_index(
        "ix_bgv_dashboard_filters",
        "background_verifications",
        ["overall_status", "employment_status", "reference_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_bgv_dashboard_filters", table_name="background_verifications")
    op.drop_index("ix_bgv_overall_status", table_name="background_verifications")
    op.drop_table("background_verifications")
