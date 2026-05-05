"""add attritions table

Revision ID: 20260504_01
Revises: 20260430_02
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_01"
down_revision = "20260430_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attritions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("separation_type", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("critical_skill", sa.String(length=255), nullable=True),
        sa.Column("is_regretted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_working_day", sa.Date(), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=True),
        sa.Column("band_name", sa.String(length=100), nullable=True),
        sa.Column("band_role", sa.String(length=255), nullable=True),
        sa.Column("project_manager", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_attritions_user_id"),
    )
    op.create_index("ix_attritions_last_working_day", "attritions", ["last_working_day"])


def downgrade() -> None:
    op.drop_index("ix_attritions_last_working_day", table_name="attritions")
    op.drop_table("attritions")
