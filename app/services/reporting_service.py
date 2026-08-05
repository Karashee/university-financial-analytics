"""Trend summary reporting service."""
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import TrendSummary


def compute_trend_summaries_dataframe(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pure aggregation step: group by (department_id, fiscal_year) and compute
    annual totals. monthly_expenditure is deduplicated to one value per
    (department_id, fiscal_year, fiscal_month) FIRST, then averaged - never
    averaged directly from the raw transaction rows. No DB access.
    """
    monthly_deduped = transactions_df.drop_duplicates(
        subset=["department_id", "fiscal_year", "fiscal_month"]
    )[["department_id", "fiscal_year", "monthly_expenditure"]]

    avg_monthly = monthly_deduped.groupby(
        ["department_id", "fiscal_year"],
        as_index=False,
    ).agg(avg_monthly_expenditure=("monthly_expenditure", "mean"))

    totals = transactions_df.groupby(
        ["department_id", "fiscal_year"],
        as_index=False,
    ).agg(
        total_annual_expenditure=("transaction_amount", "sum"),
        avg_growth_rate=("expenditure_growth_rate", "mean"),
        variance_from_historical_avg=("expenditure_variance", "mean"),
    )

    return totals.merge(avg_monthly, on=["department_id", "fiscal_year"], how="left")


def compute_trend_summaries(db: Session) -> int:
    """
    Load expenditure_transactions, compute annual trend summaries, replace
    affected trend_summaries rows, and commit. Returns the number of rows written.
    """
    connection = db.connection()
    df = pd.read_sql(
        "SELECT department_id, fiscal_year, fiscal_month, transaction_amount, "
        "monthly_expenditure, expenditure_growth_rate, expenditure_variance "
        "FROM expenditure_transactions",
        connection,
    )

    result_df = compute_trend_summaries_dataframe(df)

    affected_pairs = set(zip(result_df["department_id"], result_df["fiscal_year"]))
    for department_id, fiscal_year in affected_pairs:
        db.query(TrendSummary).filter(
            TrendSummary.department_id == department_id,
            TrendSummary.fiscal_year == fiscal_year,
        ).delete(synchronize_session=False)

    rows = [
        TrendSummary(
            department_id=row["department_id"],
            fiscal_year=int(row["fiscal_year"]),
            total_annual_expenditure=row["total_annual_expenditure"],
            avg_monthly_expenditure=row["avg_monthly_expenditure"] if pd.notna(row["avg_monthly_expenditure"]) else None,
            avg_growth_rate=row["avg_growth_rate"] if pd.notna(row["avg_growth_rate"]) else None,
            variance_from_historical_avg=row["variance_from_historical_avg"] if pd.notna(row["variance_from_historical_avg"]) else None,
        )
        for _, row in result_df.iterrows()
    ]
    db.bulk_save_objects(rows)
    db.commit()

    return len(rows)


def get_trend_summaries(
    db: Session,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    dept_id_filter: Optional[str] = None,
) -> list[TrendSummary]:
    """Query trend_summaries with optional filters."""
    query = db.query(TrendSummary)

    if dept_id_filter is not None:
        query = query.filter(TrendSummary.department_id == dept_id_filter)
    elif department_id is not None:
        query = query.filter(TrendSummary.department_id == department_id)

    if fiscal_year is not None:
        query = query.filter(TrendSummary.fiscal_year == fiscal_year)

    return query.all()
