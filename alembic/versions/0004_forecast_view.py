"""forecast view

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW vw_forecast_vs_actuals AS
        SELECT fr.department_id, d.department_name, fr.fiscal_year, fr.fiscal_month,
            fr.predicted_expenditure, fr.mae_context, fr.model_version, fr.generated_at,
            ts.total_annual_expenditure AS actual_annual_expenditure,
            ts.avg_monthly_expenditure AS actual_avg_monthly_expenditure
        FROM forecast_results fr
        JOIN departments d ON fr.department_id = d.department_id
        LEFT JOIN trend_summaries ts
            ON fr.department_id = ts.department_id AND fr.fiscal_year = ts.fiscal_year
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_forecast_vs_actuals")
