"""reporting views

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW vw_budget_utilization AS
        SELECT department_id, fiscal_year, fiscal_month, expenditure_category,
            total_transaction_amount, monthly_expenditure, budget_allocation,
            utilization_percentage, computed_at
        FROM budget_utilization_report
    """)

    op.execute("""
        CREATE OR REPLACE VIEW vw_expenditure_trends AS
        SELECT t.department_id, d.department_name, d.department_type,
            t.fiscal_year, t.fiscal_month,
            SUM(t.transaction_amount) AS total_amount,
            AVG(t.expenditure_growth_rate) AS avg_growth_rate,
            COUNT(*) AS transaction_count
        FROM expenditure_transactions t
        JOIN departments d ON t.department_id = d.department_id
        GROUP BY t.department_id, d.department_name, d.department_type,
            t.fiscal_year, t.fiscal_month
    """)

    op.execute("""
        CREATE OR REPLACE VIEW vw_vendor_category_summary AS
        SELECT vendor_category, COUNT(*) AS transaction_count,
            SUM(transaction_amount) AS total_amount,
            SUM(CASE WHEN is_anomaly_ground_truth = 1 THEN 1 ELSE 0 END) AS ground_truth_anomaly_count
        FROM expenditure_transactions
        GROUP BY vendor_category
    """)

    op.execute("""
        CREATE OR REPLACE VIEW vw_ytd_budget_utilization AS
        WITH monthly_deduped AS (
            SELECT t.department_id, t.fiscal_year, t.fiscal_month,
                MIN(t.monthly_expenditure) AS monthly_expenditure,
                b.budget_allocation
            FROM expenditure_transactions t
            LEFT JOIN budgets b
                ON t.department_id = b.department_id AND t.fiscal_year = b.fiscal_year
            GROUP BY t.department_id, t.fiscal_year, t.fiscal_month, b.budget_allocation
        ),
        ytd_calc AS (
            SELECT *,
                SUM(monthly_expenditure) OVER (
                    PARTITION BY department_id, fiscal_year
                    ORDER BY fiscal_month
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS running_ytd_expenditure
            FROM monthly_deduped
        )
        SELECT department_id, fiscal_year, fiscal_month,
            monthly_expenditure, budget_allocation, running_ytd_expenditure,
            CASE WHEN budget_allocation > 0
                THEN ROUND((running_ytd_expenditure / budget_allocation * 100)::numeric, 2)
                ELSE NULL
            END AS ytd_utilization_percentage
        FROM ytd_calc
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_ytd_budget_utilization")
    op.execute("DROP VIEW IF EXISTS vw_vendor_category_summary")
    op.execute("DROP VIEW IF EXISTS vw_expenditure_trends")
    op.execute("DROP VIEW IF EXISTS vw_budget_utilization")
