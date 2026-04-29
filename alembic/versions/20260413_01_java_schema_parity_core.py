"""core java schema parity for user_roles allocations timelog

Revision ID: 20260413_01
Revises: 20260410_01
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_01"
down_revision = "20260410_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Ensure GLOBAL/BENCH projects exist for FK backfills.
    conn.execute(
        sa.text(
            """
            INSERT INTO projects (project_code, project_name, project_type, is_active, created_at)
            VALUES ('GLOBAL', 'Global', 'IN_HOUSE', TRUE, NOW())
            ON CONFLICT (project_code) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO projects (project_code, project_name, project_type, is_active, created_at)
            VALUES ('BENCH', 'Bench', 'IN_HOUSE', TRUE, NOW())
            ON CONFLICT (project_code) DO NOTHING
            """
        )
    )

    # allocations: project_id FK semantics + designation_role + override table.
    with op.batch_alter_table("allocations") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))

    conn.execute(
        sa.text(
            """
            UPDATE allocations a
            SET project_id = p.id
            FROM projects p
            WHERE p.project_code = a.project_code
            """
        )
    )

    with op.batch_alter_table("allocations") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_allocations_project_id_projects", "projects", ["project_id"], ["id"])
        batch_op.alter_column("role", new_column_name="designation_role", existing_type=sa.String(length=100))
        batch_op.drop_column("project_code")
        batch_op.drop_column("allocation_type")

    op.create_table(
        "allocation_type_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allocation_id", sa.Integer(), nullable=False),
        sa.Column("allocation_type", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_id"),
    )

    # user_roles: composite key (user_id, role_id, project_id)
    op.create_table(
        "user_roles_v2",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id", "project_id"),
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO user_roles_v2 (user_id, role_id, project_id)
            SELECT ur.user_id, ur.role_id, COALESCE(p.id, pg.id) AS project_id
            FROM user_roles ur
            LEFT JOIN projects p ON p.project_code = ur.project_code
            JOIN projects pg ON pg.project_code = 'GLOBAL'
            GROUP BY ur.user_id, ur.role_id, COALESCE(p.id, pg.id)
            """
        )
    )

    op.drop_table("user_roles")
    op.rename_table("user_roles_v2", "user_roles")

    # timelog: java table shape
    op.create_table(
        "time_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("logged_hours", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO time_log (id, project_id, user_id, logged_hours, description, date, status, created_at, updated_at)
            SELECT
                t.id,
                p.id,
                t.user_id,
                t.hours::float,
                t.description,
                t.log_date,
                t.status,
                t.created_at,
                t.updated_at
            FROM timelogs t
            LEFT JOIN projects p ON p.project_code = t.project_code
            """
        )
    )

    op.drop_table("timelogs")


def downgrade() -> None:
    raise RuntimeError("Downgrade is not supported for this parity migration.")
