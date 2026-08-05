"""Isolation Forest anomaly detection service."""
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.features import build_isolation_forest_features
from app.ml.isolation_forest import generate_explanation, save_model, score_transactions, train_isolation_forest
from app.models import AnomalyResult, Department, ExpenditureTransaction

MODEL_VERSION = "IF_v1.0"


def run_anomaly_detection(db: Session) -> dict:
    """
    Retrain the Isolation Forest on all current transactions, score every
    transaction (flagged and normal), replace anomaly_results, and commit.
    """
    connection = db.connection()
    df = pd.read_sql(
        "SELECT transaction_id, transaction_amount, budget_utilization_percentage, "
        "expenditure_variance, historical_average_expenditure, expenditure_growth_rate, "
        "vendor_category FROM expenditure_transactions",
        connection,
    )

    feature_df = build_isolation_forest_features(df)

    model = train_isolation_forest(feature_df)
    save_model(model)

    scores_df = score_transactions(model, feature_df)

    db.query(AnomalyResult).delete(synchronize_session=False)

    rows = []
    for _, score_row in scores_df.iterrows():
        original_index = score_row["original_index"]
        transaction_id = df.loc[original_index, "transaction_id"]
        explanation = generate_explanation(feature_df.loc[original_index])
        rows.append(AnomalyResult(
            transaction_id=transaction_id,
            anomaly_score=float(score_row["anomaly_score"]),
            is_anomaly_predicted=bool(score_row["is_anomaly_predicted"]),
            explanation=explanation,
            model_version=MODEL_VERSION,
        ))

    db.bulk_save_objects(rows)
    db.commit()

    flagged_count = int(scores_df["is_anomaly_predicted"].sum())

    return {
        "total_scored": len(rows),
        "flagged_count": flagged_count,
        "model_version": MODEL_VERSION,
    }


def get_anomaly_results(
    db: Session,
    is_anomaly_predicted: Optional[bool] = None,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    dept_id_filter: Optional[str] = None,
) -> list[dict]:
    """Join anomaly_results + expenditure_transactions + departments with optional filters."""
    query = (
        db.query(AnomalyResult, ExpenditureTransaction, Department)
        .join(ExpenditureTransaction, AnomalyResult.transaction_id == ExpenditureTransaction.transaction_id)
        .join(Department, ExpenditureTransaction.department_id == Department.department_id)
    )

    if dept_id_filter is not None:
        query = query.filter(ExpenditureTransaction.department_id == dept_id_filter)
    elif department_id is not None:
        query = query.filter(ExpenditureTransaction.department_id == department_id)

    if is_anomaly_predicted is not None:
        query = query.filter(AnomalyResult.is_anomaly_predicted == is_anomaly_predicted)
    if fiscal_year is not None:
        query = query.filter(ExpenditureTransaction.fiscal_year == fiscal_year)

    results = []
    for anomaly, transaction, department in query.all():
        results.append({
            "transaction_id": anomaly.transaction_id,
            "anomaly_score": anomaly.anomaly_score,
            "is_anomaly_predicted": anomaly.is_anomaly_predicted,
            "explanation": anomaly.explanation,
            "model_version": anomaly.model_version,
            "detected_at": anomaly.detected_at,
            "department_id": transaction.department_id,
            "department_name": department.department_name,
            "department_type": department.department_type,
            "transaction_date": transaction.transaction_date,
            "transaction_amount": transaction.transaction_amount,
            "expenditure_category": transaction.expenditure_category,
            "vendor_category": transaction.vendor_category,
            "fiscal_year": transaction.fiscal_year,
            "fiscal_month": transaction.fiscal_month,
            "budget_utilization_percentage": transaction.budget_utilization_percentage,
            "expenditure_variance": transaction.expenditure_variance,
            "is_anomaly_ground_truth": transaction.is_anomaly_ground_truth,
            "anomaly_type_ground_truth": transaction.anomaly_type_ground_truth,
        })

    return results
