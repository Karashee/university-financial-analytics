"""system_logs table and vw_system_activity view for the application audit trail

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "logged_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("logger_name", sa.String(120), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("module", sa.String(120), nullable=True),
        sa.Column("function_name", sa.String(120), nullable=True),
        sa.Column("line_number", sa.Integer, nullable=True),
    )
    op.create_index("ix_system_logs_logged_at", "system_logs", ["logged_at"])
    op.create_index("ix_system_logs_level", "system_logs", ["level"])

    op.execute(
        """
        CREATE OR REPLACE VIEW vw_system_activity AS
        SELECT
            id,
            logged_at,
            level,
            logger_name,
            message,
            module,
            function_name,
            DATE(logged_at) AS log_date,
            EXTRACT(HOUR FROM logged_at)::int AS log_hour,
            CASE
                WHEN logger_name LIKE 'app.routers.%' THEN 'API'
                WHEN logger_name LIKE 'app.services.%' THEN 'Service'
                WHEN logger_name LIKE 'app.ml.%'      THEN 'ML'
                ELSE 'Core'
            END AS component
        FROM system_logs
        """
    )


def downgrade():
    op.execute("DROP VIEW IF EXISTS vw_system_activity")
    op.drop_index("ix_system_logs_level", table_name="system_logs")
    op.drop_index("ix_system_logs_logged_at", table_name="system_logs")
    op.drop_table("system_logs")
