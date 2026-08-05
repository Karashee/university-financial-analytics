"""Isolation Forest model: train, score, explain, serialize."""
import os

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest


def train_isolation_forest(feature_df: pd.DataFrame, contamination: float = 0.05) -> IsolationForest:
    """Fit an Isolation Forest on the given feature DataFrame."""
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(feature_df)
    return model


def score_transactions(model: IsolationForest, feature_df: pd.DataFrame) -> pd.DataFrame:
    """Score transactions with a trained Isolation Forest model."""
    predictions = model.predict(feature_df)  # -1 = anomaly, 1 = normal
    scores = model.decision_function(feature_df)  # lower = more anomalous

    return pd.DataFrame({
        "original_index": feature_df.index,
        "is_anomaly_predicted": predictions == -1,
        "anomaly_score": scores,
    })


def save_model(model: IsolationForest, path: str = "saved_models/isolation_forest.pkl") -> None:
    """Serialize a trained model to disk."""
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: str = "saved_models/isolation_forest.pkl") -> IsolationForest:
    """Load a serialized model from disk. Raises FileNotFoundError if missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"No saved Isolation Forest model found at: {path}")
    return joblib.load(path)


def generate_explanation(feature_row: pd.Series) -> str:
    """Generate a human-readable explanation for a scored transaction."""
    reasons = []

    if feature_row["is_unregistered_vendor"] == 1:
        reasons.append("Unregistered vendor detected")

    if feature_row["transaction_amount"] > 2 * feature_row["historical_average_expenditure"]:
        reasons.append("Transaction amount significantly exceeds historical average")

    if feature_row["budget_utilization_percentage"] > 90:
        reasons.append("Budget utilization is unusually high")

    if abs(feature_row["expenditure_variance"]) > 500000:
        reasons.append("High expenditure variance detected")

    if not reasons:
        return "Statistical outlier based on spending pattern"

    return "; ".join(reasons)
