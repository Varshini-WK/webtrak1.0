"""learning module schema for sprints 5-8

Revision ID: 20260506_01
Revises: 20260505_02
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260506_01"
down_revision = "20260505_02"
branch_labels = None
depends_on = None


material_visibility_enum = sa.Enum("HR_ONLY", "EMPLOYEE", name="training_material_visibility_enum")
attendance_status_enum = sa.Enum("PRESENT", "ABSENT", name="attendance_status_enum")


def upgrade() -> None:
    bind = op.get_bind()
    material_visibility_enum.create(bind, checkfirst=True)
    attendance_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "training_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("material_url", sa.String(length=1000), nullable=False),
        sa.Column("visibility", material_visibility_enum, nullable=False, server_default=sa.text("'EMPLOYEE'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_session_id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("attendance_status", attendance_status_enum, nullable=False),
        sa.Column("marked_by", sa.Integer(), nullable=True),
        sa.Column("marked_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_session_id"], ["training_sessions.id"]),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("training_session_id", "user_id", name="uq_training_attendance_session_user"),
    )

    op.create_table(
        "training_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column("weight_percent", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("training_id", "name", name="uq_training_assessment_training_name"),
    )

    op.create_table(
        "training_participant_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scores_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_score_percent", sa.Float(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("training_id", "user_id", name="uq_training_participant_assessment_training_user"),
    )


def downgrade() -> None:
    op.drop_table("training_participant_assessments")
    op.drop_table("training_assessments")
    op.drop_table("training_attendance")
    op.drop_table("training_materials")

    bind = op.get_bind()
    attendance_status_enum.drop(bind, checkfirst=True)
    material_visibility_enum.drop(bind, checkfirst=True)
