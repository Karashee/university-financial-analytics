"""CSV bulk ingestion service."""
import pandas as pd
from sqlalchemy.orm import Session

from app.models import Budget, Department, ExpenditureTransaction
from scripts.validate_csv import validate_csv


def _clean(value):
    """Convert pandas NaN to None; leave other values unchanged."""
    if pd.isna(value):
        return None
    return value


def ingest_csv(db: Session, filepath: str) -> dict:
    """
    Validate a CSV file and upsert valid rows into departments, budgets,
    and expenditure_transactions.

    Args:
        db: Database session
        filepath: Path to the CSV file on disk

    Returns:
        {"valid_rows": int, "inserted_rows": int, "skipped_rows": int,
         "rejected_rows": list}
    """
    validation = validate_csv(filepath)
    rejected_indices = {entry["row_index"] for entry in validation["rejected_rows"]}

    df = pd.read_csv(filepath)
    valid_df = df.drop(index=list(rejected_indices))

    # --- Upsert departments ---
    existing_department_ids = {
        row[0] for row in db.query(Department.department_id).all()
    }
    seen_department_ids = set()
    for _, row in valid_df.iterrows():
        department_id = row["Department_ID"]
        if department_id in existing_department_ids or department_id in seen_department_ids:
            continue
        seen_department_ids.add(department_id)
        db.add(Department(
            department_id=department_id,
            department_name=row["Department_Name"],
            department_type=row["Department_Type"],
        ))
    db.flush()

    # --- Upsert budgets (Budget_Allocation goes here, NOT into transactions) ---
    existing_budget_keys = {
        (row[0], row[1]) for row in db.query(Budget.department_id, Budget.fiscal_year).all()
    }
    seen_budget_keys = set()
    for _, row in valid_df.iterrows():
        budget_key = (row["Department_ID"], int(row["Fiscal_Year"]))
        if budget_key in existing_budget_keys or budget_key in seen_budget_keys:
            continue
        seen_budget_keys.add(budget_key)
        db.add(Budget(
            department_id=row["Department_ID"],
            fiscal_year=int(row["Fiscal_Year"]),
            budget_allocation=row["Budget_Allocation"],
        ))
    db.flush()

    # --- Upsert expenditure_transactions ---
    valid_transaction_ids = set(valid_df["Transaction_ID"])
    existing_transaction_ids = {
        row[0]
        for row in db.query(ExpenditureTransaction.transaction_id)
        .filter(ExpenditureTransaction.transaction_id.in_(valid_transaction_ids))
        .all()
    }

    inserted_rows = 0
    seen_transaction_ids = set()
    for _, row in valid_df.iterrows():
        transaction_id = row["Transaction_ID"]
        if transaction_id in existing_transaction_ids or transaction_id in seen_transaction_ids:
            continue
        seen_transaction_ids.add(transaction_id)

        is_anomaly = _clean(row.get("Is_Anomaly"))
        anomaly_type = _clean(row.get("Anomaly_Type"))

        db.add(ExpenditureTransaction(
            transaction_id=transaction_id,
            department_id=row["Department_ID"],
            fiscal_year=int(row["Fiscal_Year"]),
            fiscal_month=int(row["Fiscal_Month"]),
            transaction_date=pd.to_datetime(row["Transaction_Date"]).date(),
            monthly_expenditure=_clean(row.get("Monthly_Expenditure")),
            transaction_amount=row["Transaction_Amount"],
            expenditure_category=row["Expenditure_Category"],
            vendor_category=row["Vendor_Category"],
            budget_utilization_percentage=_clean(row.get("Budget_Utilization_Percentage")),
            expenditure_variance=_clean(row.get("Expenditure_Variance")),
            historical_average_expenditure=_clean(row.get("Historical_Average_Expenditure")),
            expenditure_growth_rate=_clean(row.get("Expenditure_Growth_Rate")),
            is_anomaly_ground_truth=int(is_anomaly) if is_anomaly is not None else 0,
            anomaly_type_ground_truth=str(anomaly_type) if anomaly_type is not None else "Normal",
        ))
        inserted_rows += 1

    db.commit()

    valid_rows = validation["valid_count"]
    skipped_rows = valid_rows - inserted_rows

    return {
        "valid_rows": valid_rows,
        "inserted_rows": inserted_rows,
        "skipped_rows": skipped_rows,
        "rejected_rows": validation["rejected_rows"],
    }
