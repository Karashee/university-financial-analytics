import os

import numpy as np
import pandas as pd

from app.ml.isolation_forest import (
    generate_explanation,
    load_model,
    save_model,
    score_transactions,
    train_isolation_forest,
)


def make_feature_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n_normal = 50

    normal = pd.DataFrame({
        "transaction_amount": rng.uniform(50_000, 300_000, n_normal),
        "budget_utilization_percentage": rng.uniform(10, 80, n_normal),
        "expenditure_variance": rng.uniform(-10_000, 10_000, n_normal),
        "historical_average_expenditure": rng.uniform(50_000, 300_000, n_normal),
        "expenditure_growth_rate": rng.uniform(-0.1, 0.1, n_normal),
        "is_unregistered_vendor": 0,
        "vendor_risk_score": 1,
    })

    outliers = pd.DataFrame({
        "transaction_amount": [5_000_000.0] * 3,
        "budget_utilization_percentage": [99.9] * 3,
        "expenditure_variance": [600_000.0] * 3,
        "historical_average_expenditure": [100_000.0] * 3,
        "expenditure_growth_rate": [0.5] * 3,
        "is_unregistered_vendor": 1,
        "vendor_risk_score": 3,
    })

    return pd.concat([normal, outliers], ignore_index=True)


def test_train_isolation_forest_fits_without_error():
    feature_df = make_feature_df()
    model = train_isolation_forest(feature_df)
    assert hasattr(model, "estimators_")
    assert len(model.estimators_) == 100


def test_score_transactions_returns_correct_columns():
    feature_df = make_feature_df()
    model = train_isolation_forest(feature_df)
    scores_df = score_transactions(model, feature_df)
    assert list(scores_df.columns) == ["original_index", "is_anomaly_predicted", "anomaly_score"]


def test_all_outliers_flagged_as_anomalies():
    feature_df = make_feature_df()
    model = train_isolation_forest(feature_df)
    scores_df = score_transactions(model, feature_df)
    outlier_rows = scores_df[scores_df["original_index"].isin([50, 51, 52])]
    assert len(outlier_rows) == 3
    assert outlier_rows["is_anomaly_predicted"].all()


def test_save_and_load_model_round_trip(tmp_path):
    feature_df = make_feature_df()
    model = train_isolation_forest(feature_df)
    path = str(tmp_path / "isolation_forest_test.pkl")

    save_model(model, path=path)
    assert os.path.exists(path)

    loaded_model = load_model(path=path)
    original_predictions = model.predict(feature_df)
    loaded_predictions = loaded_model.predict(feature_df)
    assert (original_predictions == loaded_predictions).all()


def test_generate_explanation_each_condition_produces_expected_substring():
    unregistered_vendor = pd.Series({
        "is_unregistered_vendor": 1,
        "transaction_amount": 10_000,
        "historical_average_expenditure": 10_000,
        "budget_utilization_percentage": 10,
        "expenditure_variance": 0,
    })
    assert "Unregistered vendor detected" in generate_explanation(unregistered_vendor)

    high_amount = pd.Series({
        "is_unregistered_vendor": 0,
        "transaction_amount": 300_000,
        "historical_average_expenditure": 100_000,
        "budget_utilization_percentage": 10,
        "expenditure_variance": 0,
    })
    assert "Transaction amount significantly exceeds historical average" in generate_explanation(high_amount)

    high_utilization = pd.Series({
        "is_unregistered_vendor": 0,
        "transaction_amount": 10_000,
        "historical_average_expenditure": 10_000,
        "budget_utilization_percentage": 95,
        "expenditure_variance": 0,
    })
    assert "Budget utilization is unusually high" in generate_explanation(high_utilization)

    high_variance = pd.Series({
        "is_unregistered_vendor": 0,
        "transaction_amount": 10_000,
        "historical_average_expenditure": 10_000,
        "budget_utilization_percentage": 10,
        "expenditure_variance": 600_000,
    })
    assert "High expenditure variance detected" in generate_explanation(high_variance)


def test_generate_explanation_fallback_when_no_conditions_triggered():
    low_row = pd.Series({
        "is_unregistered_vendor": 0,
        "transaction_amount": 10_000,
        "historical_average_expenditure": 10_000,
        "budget_utilization_percentage": 10,
        "expenditure_variance": 100,
    })
    assert generate_explanation(low_row) == "Statistical outlier based on spending pattern"
