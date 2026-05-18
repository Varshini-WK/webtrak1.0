"""migrate TALENT_POOL allocations to BENCH + billing_status; drop project

Revision ID: 20260517_01
Revises: 20260516_01
Create Date: 2026-05-17
"""

from alembic import op


revision = "20260517_01"
down_revision = "20260516_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE allocations AS a
        SET project_id = bench.id,
            billing_status = COALESCE(NULLIF(TRIM(a.billing_status), ''), 'TALENT_POOL')
        FROM projects AS tp, projects AS bench
        WHERE a.project_id = tp.id
          AND tp.project_code = 'TALENT_POOL'
          AND bench.project_code = 'BENCH'
        """
    )
    op.execute("DELETE FROM projects WHERE project_code = 'TALENT_POOL'")


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO projects (project_code, project_name, project_type, is_active, created_at)
        SELECT 'TALENT_POOL', 'Talent Pool', 'IN_HOUSE', TRUE, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM projects WHERE project_code = 'TALENT_POOL')
        """
    )
    op.execute(
        """
        UPDATE allocations AS a
        SET project_id = tp.id
        FROM projects AS tp, projects AS bench
        WHERE a.project_id = bench.id
          AND bench.project_code = 'BENCH'
          AND UPPER(TRIM(COALESCE(a.billing_status, ''))) = 'TALENT_POOL'
          AND tp.project_code = 'TALENT_POOL'
        """
    )
