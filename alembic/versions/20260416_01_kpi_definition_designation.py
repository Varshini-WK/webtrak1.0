"""add designation to kpi definitions

Revision ID: 20260416_01
Revises: 20260414_02
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260416_01"
down_revision = "20260414_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kpi_definitions", sa.Column("designation", sa.String(length=255), nullable=True))
    op.execute("UPDATE kpi_definitions SET designation = 'UNSPECIFIED' WHERE designation IS NULL")
    op.alter_column("kpi_definitions", "designation", existing_type=sa.String(length=255), nullable=False)
    op.drop_constraint("kpi_definitions_band_department_kpi_name_key", "kpi_definitions", type_="unique")
    op.create_unique_constraint(
        "kpi_definitions_band_department_designation_kpi_name_key",
        "kpi_definitions",
        ["band_id", "department", "designation", "kpi_name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "kpi_definitions_band_department_designation_kpi_name_key",
        "kpi_definitions",
        type_="unique",
    )
    op.create_unique_constraint(
        "kpi_definitions_band_department_kpi_name_key",
        "kpi_definitions",
        ["band_id", "department", "kpi_name"],
    )
    op.drop_column("kpi_definitions", "designation")
