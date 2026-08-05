import sys

import pandas as pd


def _is_null_or_empty(value) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def validate_dataframe(df: pd.DataFrame) -> dict:
    rejected_rows = []
    rejected_indices = set()

    for row_index, row in df.iterrows():
        transaction_id = row.get("Transaction_ID")

        # RULE_1_UTILIZATION: Budget_Utilization_Percentage must be numeric AND 0 <= x <= 100.
        utilization = row.get("Budget_Utilization_Percentage")
        utilization_numeric = pd.to_numeric(pd.Series([utilization]), errors="coerce").iloc[0]
        if pd.isna(utilization_numeric) or not (0 <= utilization_numeric <= 100):
            rejected_rows.append({
                "row_index": row_index,
                "transaction_id": transaction_id,
                "rule": "RULE_1_UTILIZATION",
                "detail": f"Budget_Utilization_Percentage must be numeric and between 0 and 100, got {utilization!r}",
            })
            rejected_indices.add(row_index)
            continue

        # RULE_2_AMOUNT: Transaction_Amount must be numeric AND strictly > 0.
        amount = row.get("Transaction_Amount")
        amount_numeric = pd.to_numeric(pd.Series([amount]), errors="coerce").iloc[0]
        if pd.isna(amount_numeric) or not (amount_numeric > 0):
            rejected_rows.append({
                "row_index": row_index,
                "transaction_id": transaction_id,
                "rule": "RULE_2_AMOUNT",
                "detail": f"Transaction_Amount must be numeric and strictly greater than 0, got {amount!r}",
            })
            rejected_indices.add(row_index)
            continue

        # RULE_3_VARIANCE: abs(Monthly_Expenditure - Historical_Average_Expenditure
        #   - Expenditure_Variance) <= 0.01. Skip if any of the three fields are null
        #   -- Rule 4 already catches those nulls.
        monthly_expenditure = row.get("Monthly_Expenditure")
        historical_average = row.get("Historical_Average_Expenditure")
        expenditure_variance = row.get("Expenditure_Variance")
        if not (
            _is_null_or_empty(monthly_expenditure)
            or _is_null_or_empty(historical_average)
            or _is_null_or_empty(expenditure_variance)
        ):
            difference = abs(
                float(monthly_expenditure) - float(historical_average) - float(expenditure_variance)
            )
            if difference > 0.01:
                rejected_rows.append({
                    "row_index": row_index,
                    "transaction_id": transaction_id,
                    "rule": "RULE_3_VARIANCE",
                    "detail": (
                        "abs(Monthly_Expenditure - Historical_Average_Expenditure - "
                        f"Expenditure_Variance) = {difference} exceeds 0.01"
                    ),
                })
                rejected_indices.add(row_index)
                continue

        # RULE_4_NULL: required fields must not be null or empty string.
        required_fields = [
            "Transaction_ID",
            "Department_ID",
            "Transaction_Date",
            "Expenditure_Category",
            "Fiscal_Month",
            "Fiscal_Year",
            "Monthly_Expenditure",
            "Historical_Average_Expenditure",
            "Expenditure_Variance",
        ]
        null_field = None
        for field in required_fields:
            if _is_null_or_empty(row.get(field)):
                null_field = field
                break
        if null_field is not None:
            rejected_rows.append({
                "row_index": row_index,
                "transaction_id": transaction_id,
                "rule": "RULE_4_NULL",
                "detail": f"{null_field} must not be null or empty",
            })
            rejected_indices.add(row_index)
            continue

        # RULE_5_DATE: Transaction_Date's parsed year == Fiscal_Year AND parsed month == Fiscal_Month.
        transaction_date = row.get("Transaction_Date")
        fiscal_year = row.get("Fiscal_Year")
        fiscal_month = row.get("Fiscal_Month")
        parsed_date = pd.to_datetime(transaction_date, errors="coerce")
        if pd.isna(parsed_date) or parsed_date.year != int(fiscal_year) or parsed_date.month != int(fiscal_month):
            rejected_rows.append({
                "row_index": row_index,
                "transaction_id": transaction_id,
                "rule": "RULE_5_DATE",
                "detail": (
                    f"Transaction_Date {transaction_date!r} does not match "
                    f"Fiscal_Year={fiscal_year!r}/Fiscal_Month={fiscal_month!r}"
                ),
            })
            rejected_indices.add(row_index)
            continue

    valid_count = len(df) - len(rejected_indices)
    rejected_count = len(rejected_indices)

    return {
        "valid_count": valid_count,
        "rejected_count": rejected_count,
        "rejected_rows": rejected_rows,
    }


def validate_csv(filepath: str) -> dict:
    df = pd.read_csv(filepath)
    return validate_dataframe(df)


if __name__ == "__main__":
    filepath = sys.argv[1]
    result = validate_csv(filepath)
    print(f"valid_count={result['valid_count']}")
    print(f"rejected_count={result['rejected_count']}")
    if result["rejected_rows"]:
        print("rejected_rows:")
        for entry in result["rejected_rows"]:
            print(f"  {entry}")
