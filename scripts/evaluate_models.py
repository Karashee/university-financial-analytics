"""CLI to evaluate the trained Isolation Forest and Linear Regression models against ground truth."""
import argparse
 
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine
 
from app.config import settings
from app.ml.features import build_linear_regression_features
from app.ml.linear_regression import train_linear_regression
 
 
def _evaluate_if_from_dataframes(joined_df: pd.DataFrame) -> dict:
    """
    Compute Isolation Forest evaluation metrics.
 
    joined_df columns: is_anomaly_ground_truth (int 0/1),
    is_anomaly_predicted (bool), anomaly_type_ground_truth (str).
    """
    y_true = joined_df["is_anomaly_ground_truth"].astype(int)
    y_pred = joined_df["is_anomaly_predicted"].astype(int)
 
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    matrix = confusion_matrix(y_true, y_pred).tolist()
 
    per_type_recall = {}
    for anomaly_type in joined_df["anomaly_type_ground_truth"].unique():
        if anomaly_type == "Normal":
            continue
        subset = joined_df[joined_df["anomaly_type_ground_truth"] == anomaly_type]
        per_type_recall[anomaly_type] = recall_score(
            subset["is_anomaly_ground_truth"].astype(int),
            subset["is_anomaly_predicted"].astype(int),
            zero_division=0,
        )
 
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": matrix,
        "per_type_recall": per_type_recall,
    }
 
 
def _evaluate_lr_from_arrays(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute Linear Regression evaluation metrics from true/predicted arrays."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {"mae": float(mae), "rmse": rmse, "test_size": len(y_true)}
 
 
def evaluate_isolation_forest(db_url: str) -> dict:
    """Load and join expenditure_transactions + anomaly_results, then evaluate the IF model."""
    engine = create_engine(db_url)
    joined_df = pd.read_sql(
        """
        SELECT et.is_anomaly_ground_truth, et.anomaly_type_ground_truth,
            ar.is_anomaly_predicted
        FROM expenditure_transactions et
        JOIN anomaly_results ar ON et.transaction_id = ar.transaction_id
        """,
        engine,
    )
    result = _evaluate_if_from_dataframes(joined_df)
 
    print("=== Isolation Forest Evaluation ===")
    print(f"Precision: {result['precision']:.4f}")
    print(f"Recall:    {result['recall']:.4f}")
    print(f"F1:        {result['f1']:.4f}")
    print(f"Confusion Matrix: {result['confusion_matrix']}")
    print("Per-Type Recall:")
    for anomaly_type, recall in result["per_type_recall"].items():
        print(f"  {anomaly_type}: {recall:.4f}")
 
    return result
 
 
def evaluate_linear_regression(db_url: str) -> dict:
    """
    Load expenditure_transactions + budgets, build LR features, and evaluate on a
    temporal holdout.
 
    The model is always trained fresh on the training split. The saved model in
    saved_models/ is deliberately NOT loaded here: it is trained by
    /forecasts/run on the FULL dataset, so evaluating it against X_test would
    score the model on rows it was already fitted on and report an optimistic,
    non-holdout error. Retraining on 80% of a dataset this size costs
    milliseconds and keeps the reported MAE/RMSE genuinely out-of-sample.
    """
    engine = create_engine(db_url)
    df = pd.read_sql(
        "SELECT * FROM expenditure_transactions WHERE is_anomaly_ground_truth = 0",
        engine,
    )
    budgets_df = pd.read_sql("SELECT * FROM budgets", engine)
 
    X, y = build_linear_regression_features(df, budgets_df, exclude_anomalies=False)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False, random_state=42
    )
 
    model = train_linear_regression(X_train, y_train)
 
    # X_train and X_test come from the same build_linear_regression_features call,
    # so their column order already matches. Reindexing to X_train's columns makes
    # that guarantee explicit rather than implicit, since .values discards names.
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)
 
    y_pred = model.predict(X_test.values)
    result = _evaluate_lr_from_arrays(y_test.values, y_pred)
 
    print("=== Linear Regression Evaluation ===")
    print("MAE: KES {:,.2f}".format(result["mae"]))
    print("RMSE: KES {:,.2f}".format(result["rmse"]))
    print(f"Test size: {result['test_size']}")
 
    result["model_version"] = "LR_v1.0"
    return result
 
 
def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained ML models against ground truth.")
    parser.add_argument("--model", choices=["if", "lr", "both"], default="both")
    args = parser.parse_args()
 
    db_url = settings.database_url
 
    if args.model in ("if", "both"):
        evaluate_isolation_forest(db_url)
    if args.model in ("lr", "both"):
        evaluate_linear_regression(db_url)
 
 
if __name__ == "__main__":
    main()
 