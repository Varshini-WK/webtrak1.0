"""reference data: kpi_definitions, webknot_value, submission_cycles, designation

Revision ID: 20260414_01
Revises: 20260413_02
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_01"
down_revision = "20260413_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kpi_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("band_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=50), nullable=False),
        sa.Column("kpi_name", sa.String(length=255), nullable=False),
        sa.Column("weightage", sa.Numeric(5, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["band_id"], ["bands.id"], name="fk_kpi_definitions_band_id_bands"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("band_id", "department", "kpi_name", name="kpi_definitions_band_department_kpi_name_key"),
    )

    op.create_table(
        "webknot_value",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("evaluation_criteria", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "submission_cycles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cycle_key", sa.String(length=7), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("window_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cycle_key", "scope", name="submission_cycles_cycle_key_scope_key"),
    )

    op.create_table(
        "designation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("band_id", sa.Integer(), nullable=True),
        sa.Column("department", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["band_id"], ["bands.id"], name="fk_designation_band_id_bands"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("designation")
    op.drop_table("submission_cycles")
    op.drop_table("webknot_value")
    op.drop_table("kpi_definitions")
