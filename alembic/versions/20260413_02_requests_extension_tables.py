"""add request and extension workflow tables

Revision ID: 20260413_02
Revises: 20260413_01
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_02"
down_revision = "20260413_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_from_date", sa.Date(), nullable=False),
        sa.Column("request_to_date", sa.Date(), nullable=False),
        sa.Column("request_type", sa.String(length=20), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_half_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reference_file_url", sa.String(length=500), nullable=True),
        sa.Column("manager_comp_off_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_requests_user_id", "user_requests", ["user_id"])
    op.create_index("ix_user_requests_dates", "user_requests", ["request_from_date", "request_to_date"])
    op.create_index("ix_user_requests_type_status", "user_requests", ["request_type", "status"])

    op.create_table(
        "user_request_tracking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("user_request_id", sa.Integer(), nullable=False),
        sa.Column("actioner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["actioner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_request_tracking_user_request", "user_request_tracking", ["user_request_id"])
    op.create_index("ix_user_request_tracking_actioner", "user_request_tracking", ["actioner_id"])

    op.create_table(
        "leave_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_request_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("for_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("comments", sa.String(length=255), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leave_transactions_user_date", "leave_transactions", ["user_id", "for_date"])

    op.create_table(
        "allocation_extension_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allocation_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("current_end_date", sa.Date(), nullable=False),
        sa.Column("requested_end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allocation_extension_requests_allocation", "allocation_extension_requests", ["allocation_id"])
    op.create_index("ix_allocation_extension_requests_status", "allocation_extension_requests", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=True),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_receiver_created", "notifications", ["receiver_id", "created_at"])

    # Start-clean dedicated Comp-Off tables (no backfill from leave ledgers).
    op.create_table(
        "comp_off_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_request_id", sa.Integer(), nullable=True),
        sa.Column("grant_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("units", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("remaining_units", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comp_off_grants_user_expiry", "comp_off_grants", ["user_id", "expiry_date"])

    op.create_table(
        "comp_off_approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_request_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comp_off_approvals_request", "comp_off_approvals", ["user_request_id"])

    op.create_table(
        "comp_off_usages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grant_id", sa.Integer(), nullable=False),
        sa.Column("user_request_id", sa.Integer(), nullable=False),
        sa.Column("used_units", sa.Float(), nullable=False),
        sa.Column("used_for_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["grant_id"], ["comp_off_grants.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comp_off_usages_grant", "comp_off_usages", ["grant_id"])


def downgrade() -> None:
    raise RuntimeError("Downgrade is not supported for this migration.")
