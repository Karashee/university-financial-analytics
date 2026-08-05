"""anomaly views

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW vw_anomaly_flagged AS
        SELECT ar.transaction_id, ar.anomaly_score, ar.is_anomaly_predicted,
            ar.explanation, ar.model_version, ar.detected_at,
            et.department_id, d.department_name, d.department_type,
            et.transaction_date, et.transaction_amount, et.expenditure_category,
            et.vendor_category, et.fiscal_year, et.fiscal_month,
            et.budget_utilization_percentage, et.expenditure_variance,
            et.is_anomaly_ground_truth, et.anomaly_type_ground_truth
        FROM anomaly_results ar
        JOIN expenditure_transactions et ON ar.transaction_id = et.transaction_id
        JOIN departments d ON et.department_id = d.department_id
        WHERE ar.is_anomaly_predicted = true
    """)

    op.execute("""
        CREATE OR REPLACE VIEW vw_anomaly_comparison AS
        SELECT et.transaction_id, et.is_anomaly_ground_truth, ar.is_anomaly_predicted,
            et.anomaly_type_ground_truth, ar.explanation, ar.anomaly_score,
            et.department_id, et.fiscal_year, et.fiscal_month, et.transaction_amount
        FROM expenditure_transactions et
        LEFT JOIN anomaly_results ar ON et.transaction_id = ar.transaction_id
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_anomaly_comparison")
    op.execute("DROP VIEW IF EXISTS vw_anomaly_flagged")
