"""Budget utilization analytics service."""
from typing import Optional
 
import pandas as pd
from sqlalchemy.orm import Session
 
from app.models import BudgetUtilizationReport
 
 
def compute_budget_utilization_dataframe(
    transactions_df: pd.DataFrame,
    budgets_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Pure aggregation step: left-join transactions to budgets on
    (department_id, fiscal_year), group by (department_id, fiscal_year,
    fiscal_month, expenditure_category), and compute utilization.
 
    No DB access - operates entirely on already-loaded DataFrames so it
    can be unit tested without a database.
    """
    merged = transactions_df.merge(
        budgets_df,
        on=["department_id", "fiscal_year"],
        how="left",
    )
 
    grouped = merged.groupby(
        ["department_id", "fiscal_year", "fiscal_month", "expenditure_category"],
        as_index=False,
    ).agg(
        total_transaction_amount=("transaction_amount", "sum"),
        monthly_expenditure=("monthly_expenditure", "first"),
        budget_allocation=("budget_allocation", "first"),
    )
 
    def _utilization(row):
        allocation = row["budget_allocation"]
        if pd.isna(allocation) or allocation == 0:
            return None
        return (row["total_transaction_amount"] / allocation) * 100
 
    grouped["utilization_percentage"] = grouped.apply(_utilization, axis=1)
 
    return grouped
 
 
def compute_budget_utilization(db: Session) -> int:
    """
    Load expenditure_transactions and budgets from PostgreSQL, compute
    per-group utilization, replace affected budget_utilization_report rows,
    and commit. Returns the number of rows written.
    """
    connection = db.connection()
 
    transactions_df = pd.read_sql(
        "SELECT department_id, fiscal_year, fiscal_month, expenditure_category, "
        "transaction_amount, monthly_expenditure FROM expenditure_transactions",
        connection,
    )
    budgets_df = pd.read_sql(
        "SELECT department_id, fiscal_year, budget_allocation FROM budgets",
        connection,
    )
 
    result_df = compute_budget_utilization_dataframe(transactions_df, budgets_df)
 
    affected_pairs = set(
        zip(result_df["department_id"], result_df["fiscal_year"])
    )
    for department_id, fiscal_year in affected_pairs:
        db.query(BudgetUtilizationReport).filter(
            BudgetUtilizationReport.department_id == department_id,
            BudgetUtilizationReport.fiscal_year == fiscal_year,
        ).delete(synchronize_session=False)
 
    rows = [
        BudgetUtilizationReport(
            department_id=row["department_id"],
            fiscal_year=int(row["fiscal_year"]),
            fiscal_month=int(row["fiscal_month"]),
            expenditure_category=row["expenditure_category"],
            total_transaction_amount=row["total_transaction_amount"],
            monthly_expenditure=row["monthly_expenditure"] if pd.notna(row["monthly_expenditure"]) else None,
            budget_allocation=row["budget_allocation"] if pd.notna(row["budget_allocation"]) else None,
            utilization_percentage=row["utilization_percentage"],
        )
        for _, row in result_df.iterrows()
    ]
    db.bulk_save_objects(rows)
    db.commit()
 
    return len(rows)
 
 
def compute_variance_dataframe(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pure aggregation step: group by (department_id, fiscal_year, fiscal_month)
    and compute variance statistics. No DB access.
    """
    grouped = transactions_df.groupby(
        ["department_id", "fiscal_year", "fiscal_month"],
        as_index=False,
    ).agg(
        avg_expenditure_variance=("expenditure_variance", "mean"),
        std_dev_variance=("expenditure_variance", lambda s: s.std(ddof=1)),
        avg_historical_average_expenditure=("historical_average_expenditure", "mean"),
    )
 
    grouped["std_dev_variance"] = grouped["std_dev_variance"].fillna(0.0)
    grouped["flag_high_variance"] = grouped["avg_expenditure_variance"].abs() > (
        2 * grouped["avg_historical_average_expenditure"]
    )
 
    return grouped.drop(columns=["avg_historical_average_expenditure"])
 
 
def compute_variance_report(
    db: Session,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    dept_id_filter: Optional[str] = None,
) -> list[dict]:
    """
    Load expenditure_transactions, optionally filter by department and fiscal
    year, and compute variance statistics per (department_id, fiscal_year,
    fiscal_month). Does not write to a table.
 
    dept_id_filter is the role-derived restriction (a department_head may only
    see their own department) and overrides any caller-supplied department_id,
    matching the pattern used by get_budget_utilization_report.
    """
    connection = db.connection()
    df = pd.read_sql(
        "SELECT department_id, fiscal_year, fiscal_month, expenditure_variance, "
        "historical_average_expenditure FROM expenditure_transactions",
        connection,
    )
 
    if dept_id_filter is not None:
        df = df[df["department_id"] == dept_id_filter]
    elif department_id is not None:
        df = df[df["department_id"] == department_id]
 
    if fiscal_year is not None:
        df = df[df["fiscal_year"] == fiscal_year]
 
    result_df = compute_variance_dataframe(df)
    return result_df.to_dict(orient="records")
 
 
def compute_growth_rate_dataframe(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Pure aggregation step: group by (department_id, fiscal_year) and average growth rate."""
    return transactions_df.groupby(
        ["department_id", "fiscal_year"],
        as_index=False,
    ).agg(avg_growth_rate=("expenditure_growth_rate", "mean"))
 
 
def compute_growth_rate_summary(
    db: Session,
    department_id: Optional[str] = None,
    dept_id_filter: Optional[str] = None,
) -> list[dict]:
    """
    Load expenditure_transactions, optionally filter by department, and
    compute average growth rate per (department_id, fiscal_year).
    Does not write to a table.
 
    dept_id_filter is the role-derived restriction and overrides any
    caller-supplied department_id.
    """
    connection = db.connection()
    df = pd.read_sql(
        "SELECT department_id, fiscal_year, expenditure_growth_rate FROM expenditure_transactions",
        connection,
    )
 
    if dept_id_filter is not None:
        df = df[df["department_id"] == dept_id_filter]
    elif department_id is not None:
        df = df[df["department_id"] == department_id]
 
    result_df = compute_growth_rate_dataframe(df)
    return result_df.to_dict(orient="records")
 
 
def get_budget_utilization_report(
    db: Session,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_month: Optional[int] = None,
    expenditure_category: Optional[str] = None,
    dept_id_filter: Optional[str] = None,
) -> list[BudgetUtilizationReport]:
    """Query budget_utilization_report with optional filters."""
    query = db.query(BudgetUtilizationReport)
 
    if dept_id_filter is not None:
        query = query.filter(BudgetUtilizationReport.department_id == dept_id_filter)
    elif department_id is not None:
        query = query.filter(BudgetUtilizationReport.department_id == department_id)
 
    if fiscal_year is not None:
        query = query.filter(BudgetUtilizationReport.fiscal_year == fiscal_year)
    if fiscal_month is not None:
        query = query.filter(BudgetUtilizationReport.fiscal_month == fiscal_month)
    if expenditure_category is not None:
        query = query.filter(BudgetUtilizationReport.expenditure_category == expenditure_category)
 
    return query.all()

    