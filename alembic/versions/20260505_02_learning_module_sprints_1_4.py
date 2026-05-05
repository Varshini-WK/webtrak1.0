"""learning module schema for sprints 1-4

Revision ID: 20260505_02
Revises: 20260505_01
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260505_02"
down_revision = "20260505_01"
branch_labels = None
depends_on = None


training_category_enum = sa.Enum("PROFESSIONAL", "TECHNICAL", "SOFT_SKILLS", name="training_category_enum")
training_type_enum = sa.Enum("MANDATORY", "OPTIONAL", "HYBRID", name="training_type_enum")
training_status_enum = sa.Enum("DRAFT", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="training_status_enum")
training_mode_enum = sa.Enum("ONLINE", "OFFLINE", "HYBRID", name="training_mode_enum")
participant_source_enum = sa.Enum("ASSIGNED", "SELF_ENROLLED", name="participant_source_enum")
enrollment_status_enum = sa.Enum("WITHDRAWN", "COMPLETED", name="enrollment_status_enum")


def upgrade() -> None:
    bind = op.get_bind()
    training_category_enum.create(bind, checkfirst=True)
    training_type_enum.create(bind, checkfirst=True)
    training_status_enum.create(bind, checkfirst=True)
    training_mode_enum.create(bind, checkfirst=True)
    participant_source_enum.create(bind, checkfirst=True)
    enrollment_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "trainings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", training_category_enum, nullable=False),
        sa.Column("type", training_type_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("status", training_status_enum, nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_trainers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("trainer_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.ForeignKeyConstraint(["trainer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("training_id", "trainer_user_id", name="uq_training_trainers_training_user"),
    )

    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("mode", training_mode_enum, nullable=False),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("participant_source", participant_source_enum, nullable=False),
        sa.Column("enrollment_status", enrollment_status_enum, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("training_id", "user_id", name="uq_training_participants_training_user"),
    )


def downgrade() -> None:
    op.drop_table("training_participants")
    op.drop_table("training_sessions")
    op.drop_table("training_trainers")
    op.drop_table("trainings")

    bind = op.get_bind()
    enrollment_status_enum.drop(bind, checkfirst=True)
    participant_source_enum.drop(bind, checkfirst=True)
    training_mode_enum.drop(bind, checkfirst=True)
    training_status_enum.drop(bind, checkfirst=True)
    training_type_enum.drop(bind, checkfirst=True)
    training_category_enum.drop(bind, checkfirst=True)
