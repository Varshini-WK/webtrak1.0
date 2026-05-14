"""projects: client name and account manager

Revision ID: 20260513_01
Revises: 20260506_01
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_01"
down_revision = "20260506_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("client_name", sa.String(length=255), nullable=True))
    op.add_column("projects", sa.Column("account_manager_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_account_manager_user_id_users",
        "projects",
        "users",
        ["account_manager_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_account_manager_user_id_users", "projects", type_="foreignkey")
    op.drop_column("projects", "account_manager_user_id")
    op.drop_column("projects", "client_name")
