"""Linear Regression model: train, forecast, evaluate, serialize."""
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


def train_linear_regression(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    """Fit a Linear Regression model."""
    model = LinearRegression()
    model.fit(X_train.values, y_train.values)
    return model


def generate_forecasts(
    model: LinearRegression,
    X_df: pd.DataFrame,
    department_ids,
    fiscal_years,
    fiscal_months,
) -> pd.DataFrame:
    """Predict expenditure for the given feature rows, clipped to be non-negative."""
    raw = model.predict(X_df.values)
    predicted_expenditure = np.clip(raw, 0, None)

    return pd.DataFrame({
        "department_id": list(department_ids),
        "fiscal_year": list(fiscal_years),
        "fiscal_month": list(fiscal_months),
        "predicted_expenditure": predicted_expenditure,
    })


def compute_mae(model: LinearRegression, X_test: pd.DataFrame, y_test: pd.Series) -> float:
    """Mean absolute error of the model's predictions on a held-out set."""
    return mean_absolute_error(y_test.values, model.predict(X_test.values))


def save_lr_model(
    model: LinearRegression,
    feature_cols: list[str],
    path: str = "saved_models/linear_regression.pkl"
) -> None:
    """Serialize the trained model together with its feature column order."""
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols}, path)


def load_lr_model(path: str = "saved_models/linear_regression.pkl") -> tuple[LinearRegression, list[str]]:
    """Load a serialized model and its feature column order. Raises FileNotFoundError if missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"No saved Linear Regression model found at: {path}")
    payload = joblib.load(path)
    return payload["model"], payload["feature_cols"]


def prepare_future_months(
    unique_depts,
    dept_last_month: dict,
    dept_means: dict,
    dept_growth: dict,
    dept_hist_avg: dict,
    dept_budget: dict,
    feature_cols: list[str],
    n_months: int,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Build skeleton feature rows for the next n_months per department, for use
    with a trained Linear Regression model's predict().

    dept_last_month holds (last_fiscal_year, last_fiscal_month,
    last_monthly_expenditure) per department. lag_1_expenditure for each
    department's first forecasted month uses that last actual expenditure.
    dept_means (a true department-level mean, unlike dept_last_month's last
    actual value) is accepted for signature/caller consistency but is not
    itself used to seed the lag. Correctly chaining lag_1 to the prior
    FORECAST for month 2+ requires the model's own output, which this
    function has no access to (it accepts no model) - for genuine
    multi-step-ahead forecasting, call this function iteratively with
    n_months=1, updating dept_last_month's last-actual value with each new
    prediction before the next call. When n_months > 1 in a single call,
    lag_1 for month 2+ is carried forward from month 1's anchor value as a
    naive placeholder.
    """
    department_id_list = []
    fiscal_year_list = []
    fiscal_month_list = []
    rows = []

    for dept in unique_depts:
        year, month, lag_value = dept_last_month[dept]

        for _ in range(n_months):
            month += 1
            if month > 12:
                month = 1
                year += 1

            rows.append({
                "fiscal_month": month,
                "fiscal_year": year,
                "historical_average_expenditure": dept_hist_avg[dept],
                "expenditure_growth_rate": dept_growth[dept],
                "budget_allocation": dept_budget.get(dept, 0.0),
                "lag_1_expenditure": lag_value,
                f"dept_{dept}": 1,
            })
            department_id_list.append(dept)
            fiscal_year_list.append(year)
            fiscal_month_list.append(month)

    # Rows from different departments carry different dept_* keys, so building
    # the DataFrame from a list of dicts leaves NaN (not 0) in a department's
    # non-matching dummy columns - reindex's fill_value only backfills columns
    # absent from the frame entirely, not NaN cells in columns already present.
    X_df = pd.DataFrame(rows)
    dummy_columns = [col for col in X_df.columns if col.startswith("dept_")]
    X_df[dummy_columns] = X_df[dummy_columns].fillna(0)
    X_df = X_df.reindex(columns=feature_cols, fill_value=0)

    dept_id_series = pd.Series(department_id_list, name="department_id")
    year_series = pd.Series(fiscal_year_list, name="fiscal_year")
    month_series = pd.Series(fiscal_month_list, name="fiscal_month")

    return X_df, dept_id_series, year_series, month_series
