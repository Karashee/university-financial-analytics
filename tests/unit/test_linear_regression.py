import os

import pandas as pd

from app.ml.linear_regression import (
    compute_mae,
    generate_forecasts,
    load_lr_model,
    prepare_future_months,
    save_lr_model,
    train_linear_regression,
)

FEATURE_COLUMNS = [
    "fiscal_month",
    "budget_allocation",
    "lag_1_expenditure",
    "dept_DEPT01",
    "dept_DEPT02",
]


def make_linear_dataset() -> tuple[pd.DataFrame, pd.Series]:
    """y = 500_000 + 50_000 * fiscal_month, 2 departments x 6 months, no noise."""
    months = list(range(1, 7))
    rows = []
    for dept, budget in [("DEPT01", 1_000_000.0), ("DEPT02", 2_000_000.0)]:
        y_values = [500_000.0 + 50_000.0 * m for m in months]
        for idx, m in enumerate(months):
            # Extrapolate the same linear trend backward for month 1's "previous"
            # value (m=1 -> lag uses the month-0 equivalent), so lag_1 stays an
            # exact linear function of fiscal_month with no discontinuity - this
            # keeps the synthetic dataset perfectly, noiselessly linear.
            lag = 500_000.0 + 50_000.0 * (m - 1)
            rows.append({
                "fiscal_month": m,
                "budget_allocation": budget,
                "lag_1_expenditure": lag,
                "dept_DEPT01": 1 if dept == "DEPT01" else 0,
                "dept_DEPT02": 1 if dept == "DEPT02" else 0,
                "monthly_expenditure": y_values[idx],
            })

    df = pd.DataFrame(rows)
    X = df[FEATURE_COLUMNS]
    y = df["monthly_expenditure"]
    return X, y


def test_train_linear_regression_fits():
    X, y = make_linear_dataset()
    model = train_linear_regression(X, y)
    assert model.coef_ is not None


def test_generate_forecasts_returns_correct_columns():
    X, y = make_linear_dataset()
    model = train_linear_regression(X, y)
    forecasts = generate_forecasts(
        model, X,
        department_ids=["DEPT01"] * len(X),
        fiscal_years=[2023] * len(X),
        fiscal_months=X["fiscal_month"].tolist(),
    )
    assert list(forecasts.columns) == [
        "department_id", "fiscal_year", "fiscal_month", "predicted_expenditure",
    ]


def test_negative_prediction_clipped_to_zero():
    X, y = make_linear_dataset()
    model = train_linear_regression(X, y)

    # Some training features are collinear (fiscal_month, lag_1_expenditure,
    # and the dept dummies all move together), so OLS can distribute the
    # fitted slope across them in any combination. Build a row from the
    # model's own coefficients - for each feature, push it in whichever
    # direction makes coef_i * x_i very negative - so the raw prediction is
    # guaranteed strongly negative regardless of that split.
    extreme_values = [-1e9 if coef >= 0 else 1e9 for coef in model.coef_]
    extreme_row = pd.DataFrame([extreme_values], columns=FEATURE_COLUMNS)

    forecasts = generate_forecasts(
        model, extreme_row,
        department_ids=["DEPT01"],
        fiscal_years=[2023],
        fiscal_months=[-1000],
    )
    assert forecasts.iloc[0]["predicted_expenditure"] == 0.0


def test_compute_mae_near_zero_on_perfectly_linear_data():
    X, y = make_linear_dataset()
    model = train_linear_regression(X, y)
    mae = compute_mae(model, X, y)
    assert mae < 1e-6


def test_save_and_load_lr_model_round_trip(tmp_path):
    X, y = make_linear_dataset()
    model = train_linear_regression(X, y)
    path = str(tmp_path / "lr_test.pkl")

    save_lr_model(model, FEATURE_COLUMNS, path=path)
    assert os.path.exists(path)

    loaded_model, loaded_feature_cols = load_lr_model(path=path)
    assert loaded_feature_cols == FEATURE_COLUMNS

    original_predictions = model.predict(X.values)
    loaded_predictions = loaded_model.predict(X.values)
    assert (original_predictions == loaded_predictions).all()


def test_prepare_future_months_december_rolls_to_january_next_year():
    feature_cols = FEATURE_COLUMNS + ["fiscal_year", "historical_average_expenditure"]
    X_df, dept_id_series, year_series, month_series = prepare_future_months(
        unique_depts=["DEPT01"],
        dept_last_month={"DEPT01": (2023, 12, 550_000.0)},
        dept_means={"DEPT01": 550_000.0},
        dept_growth={"DEPT01": 0.05},
        dept_hist_avg={"DEPT01": 500_000.0},
        dept_budget={"DEPT01": 1_000_000.0},
        feature_cols=feature_cols,
        n_months=1,
    )
    assert year_series.iloc[0] == 2024
    assert month_series.iloc[0] == 1
    assert dept_id_series.iloc[0] == "DEPT01"


def test_prepare_future_months_budget_allocation_matches_dept_budget():
    X_df, _, _, _ = prepare_future_months(
        unique_depts=["DEPT01"],
        dept_last_month={"DEPT01": (2023, 6, 550_000.0)},
        dept_means={"DEPT01": 550_000.0},
        dept_growth={"DEPT01": 0.05},
        dept_hist_avg={"DEPT01": 500_000.0},
        dept_budget={"DEPT01": 1_234_567.0},
        feature_cols=FEATURE_COLUMNS,
        n_months=1,
    )
    assert X_df.iloc[0]["budget_allocation"] == 1_234_567.0


def test_prepare_future_months_result_columns_match_feature_cols():
    X_df, _, _, _ = prepare_future_months(
        unique_depts=["DEPT01"],
        dept_last_month={"DEPT01": (2023, 6, 550_000.0)},
        dept_means={"DEPT01": 550_000.0},
        dept_growth={"DEPT01": 0.05},
        dept_hist_avg={"DEPT01": 500_000.0},
        dept_budget={"DEPT01": 1_000_000.0},
        feature_cols=FEATURE_COLUMNS,
        n_months=1,
    )
    assert list(X_df.columns) == FEATURE_COLUMNS
