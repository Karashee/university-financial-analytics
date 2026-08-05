"""Linear Regression expenditure forecast service."""
from typing import Optional
 
import pandas as pd
from sqlalchemy.orm import Session
 
from app.ml.features import build_linear_regression_features, get_lr_feature_columns
from app.ml.linear_regression import (
    compute_mae,
    generate_forecasts,
    prepare_future_months,
    save_lr_model,
    train_linear_regression,
)
from app.models import Department, ForecastResult
 
MODEL_VERSION = "LR_v1.0"
 
 
def run_expenditure_forecast(db: Session, n_months: int = 3) -> dict:
    """
    Retrain the Linear Regression model on all current transactions, forecast
    n_months ahead for every department, replace forecast_results, and commit.
 
    Forecasts are generated one month at a time: each step's predicted
    expenditure is fed back into dept_last_month as the next step's
    lag_1_expenditure anchor, so month 2+ reflects the model's own prior
    forecast rather than a frozen last-actual value. See
    app.ml.linear_regression.prepare_future_months docstring for why this
    chaining has to happen at the caller level.
    """
    connection = db.connection()
    df = pd.read_sql("SELECT * FROM expenditure_transactions", connection)
    budgets_df = pd.read_sql(
        "SELECT department_id, fiscal_year, budget_allocation FROM budgets",
        connection,
    )
 
    X_train, y_train = build_linear_regression_features(df, budgets_df, exclude_anomalies=True)
 
    model = train_linear_regression(X_train, y_train)
    feature_cols = get_lr_feature_columns(X_train)
    save_lr_model(model, feature_cols)
 
    mae = compute_mae(model, X_train, y_train)
 
    # Deduplicated monthly view built from ALL actual transactions (not the
    # exclude_anomalies-filtered training set) - used purely to establish each
    # department's true last-observed month and historical statistics.
    monthly_df = (
        df.merge(budgets_df, on=["department_id", "fiscal_year"], how="left")
        .groupby(["department_id", "fiscal_year", "fiscal_month"], as_index=False)
        .agg(
            monthly_expenditure=("monthly_expenditure", "first"),
            expenditure_growth_rate=("expenditure_growth_rate", "first"),
            historical_average_expenditure=("historical_average_expenditure", "first"),
            budget_allocation=("budget_allocation", "first"),
        )
        .sort_values(["department_id", "fiscal_year", "fiscal_month"])
    )
 
    unique_depts = sorted(monthly_df["department_id"].unique())
 
    dept_last_month = {}
    dept_means = {}
    dept_growth = {}
    dept_hist_avg = {}
    dept_budget = {}
 
    for dept in unique_depts:
        dept_rows = monthly_df[monthly_df["department_id"] == dept]
        last_row = dept_rows.iloc[-1]
 
        dept_last_month[dept] = (
            int(last_row["fiscal_year"]),
            int(last_row["fiscal_month"]),
            float(last_row["monthly_expenditure"]),
        )
        dept_means[dept] = float(dept_rows["monthly_expenditure"].mean())
        dept_growth[dept] = float(dept_rows["expenditure_growth_rate"].mean())
        dept_hist_avg[dept] = float(dept_rows["historical_average_expenditure"].mean())
 
        latest_year = dept_rows["fiscal_year"].max()
        latest_year_rows = dept_rows[dept_rows["fiscal_year"] == latest_year]
        latest_budget = latest_year_rows["budget_allocation"].iloc[-1]
        dept_budget[dept] = float(latest_budget) if pd.notna(latest_budget) else 0.0
 
    # Generate one month at a time so lag_1_expenditure for month 2+ reflects
    # the model's own prior prediction, not a frozen last-actual value.
    step_results = []
    for _ in range(n_months):
        X_fc, dept_ids, years, months = prepare_future_months(
            unique_depts, dept_last_month, dept_means, dept_growth,
            dept_hist_avg, dept_budget, feature_cols, 1,
        )
        X_fc = X_fc.reindex(columns=feature_cols, fill_value=0)
 
        step_df = generate_forecasts(model, X_fc, dept_ids, years, months)
        step_results.append(step_df)
 
        # Chain: this step's prediction becomes next step's lag anchor.
        for _, row in step_df.iterrows():
            dept_last_month[row["department_id"]] = (
                int(row["fiscal_year"]),
                int(row["fiscal_month"]),
                float(row["predicted_expenditure"]),
            )
 
    forecasts_df = pd.concat(step_results, ignore_index=True)
 
    db.query(ForecastResult).delete(synchronize_session=False)
 
    rows = [
        ForecastResult(
            department_id=row["department_id"],
            fiscal_year=int(row["fiscal_year"]),
            fiscal_month=int(row["fiscal_month"]),
            predicted_expenditure=float(row["predicted_expenditure"]),
            mae_context=float(mae),
            model_version=MODEL_VERSION,
        )
        for _, row in forecasts_df.iterrows()
    ]
    db.bulk_save_objects(rows)
    db.commit()
 
    return {
        "total_forecasts": len(rows),
        "mae_context": float(mae),
        "n_months_ahead": n_months,
        "model_version": MODEL_VERSION,
    }
 
 
def get_forecast_results(
    db: Session,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    dept_id_filter: Optional[str] = None,
) -> list[dict]:
    """Join forecast_results + departments with optional filters."""
    query = db.query(ForecastResult, Department).join(
        Department, ForecastResult.department_id == Department.department_id
    )
 
    if dept_id_filter is not None:
        query = query.filter(ForecastResult.department_id == dept_id_filter)
    elif department_id is not None:
        query = query.filter(ForecastResult.department_id == department_id)
 
    if fiscal_year is not None:
        query = query.filter(ForecastResult.fiscal_year == fiscal_year)
 
    results = []
    for forecast, department in query.all():
        results.append({
            "department_id": forecast.department_id,
            "department_name": department.department_name,
            "fiscal_year": forecast.fiscal_year,
            "fiscal_month": forecast.fiscal_month,
            "predicted_expenditure": forecast.predicted_expenditure,
            "mae_context": forecast.mae_context,
            "model_version": forecast.model_version,
            "generated_at": forecast.generated_at,
        })
 
    return results
 