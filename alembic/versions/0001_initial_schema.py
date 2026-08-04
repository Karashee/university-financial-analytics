"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-08-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create departments table
    op.create_table(
        'departments',
        sa.Column('department_id', sa.String(length=10), nullable=False),
        sa.Column('department_name', sa.String(length=100), nullable=False),
        sa.Column('department_type', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('department_id')
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False, server_default=text("uuid_generate_v4()")),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=200), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'])
    )
    
    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('department_id', sa.String(length=10), nullable=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('budget_allocation', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'fiscal_year', name='uq_budgets_dept_year'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'])
    )
    
    # Create expenditure_transactions table
    op.create_table(
        'expenditure_transactions',
        sa.Column('transaction_id', sa.String(length=20), nullable=False),
        sa.Column('department_id', sa.String(length=10), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_month', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('monthly_expenditure', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('transaction_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('expenditure_category', sa.String(length=100), nullable=False),
        sa.Column('vendor_category', sa.String(length=100), nullable=False),
        sa.Column('budget_utilization_percentage', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('expenditure_variance', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('historical_average_expenditure', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('expenditure_growth_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('is_anomaly_ground_truth', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('anomaly_type_ground_truth', sa.String(length=100), nullable=True, server_default="'Normal'"),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('transaction_id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'])
    )
    
    # Create anomaly_results table
    op.create_table(
        'anomaly_results',
        sa.Column('id', sa.UUID(), nullable=False, server_default=text("uuid_generate_v4()")),
        sa.Column('transaction_id', sa.String(length=20), nullable=True),
        sa.Column('anomaly_score', sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column('is_anomaly_predicted', sa.Boolean(), nullable=False),
        sa.Column('explanation', sa.String(length=500), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('detected_at', sa.TIMESTAMP(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transaction_id'], ['expenditure_transactions.transaction_id'])
    )
    
    # Create forecast_results table
    op.create_table(
        'forecast_results',
        sa.Column('id', sa.UUID(), nullable=False, server_default=text("uuid_generate_v4()")),
        sa.Column('department_id', sa.String(length=10), nullable=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_month', sa.Integer(), nullable=False),
        sa.Column('predicted_expenditure', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('mae_context', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('generated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'])
    )
    
    # Create budget_utilization_report table
    op.create_table(
        'budget_utilization_report',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('department_id', sa.String(length=10), nullable=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_month', sa.Integer(), nullable=False),
        sa.Column('expenditure_category', sa.String(length=100), nullable=True),
        sa.Column('total_transaction_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('monthly_expenditure', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('budget_allocation', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('utilization_percentage', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('computed_at', sa.TIMESTAMP(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'])
    )
    
    # Create trend_summaries table
    op.create_table(
        'trend_summaries',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('department_id', sa.String(length=10), nullable=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('total_annual_expenditure', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('avg_monthly_expenditure', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('avg_growth_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('variance_from_historical_avg', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('computed_at', sa.TIMESTAMP(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'])
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('trend_summaries')
    op.drop_table('budget_utilization_report')
    op.drop_table('forecast_results')
    op.drop_table('anomaly_results')
    op.drop_table('expenditure_transactions')
    op.drop_table('budgets')
    op.drop_table('users')
    op.drop_table('departments')
    op.drop_table('roles')
    
    # Drop UUID extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
