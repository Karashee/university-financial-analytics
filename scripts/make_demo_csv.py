"""
Build a demo upload CSV for the web UI walkthrough.

Reads the full synthetic dataset (never modified) and writes
data/demo_upload.csv: every original row, plus three invalid rows appended
at the end, each designed to fail exactly one validation rule so the demo
can show the rejected-rows table.
"""
import pandas as pd

from scripts.validate_csv import validate_csv

SOURCE_CSV = "data/synthetic_university_financial_data_final.csv"
OUTPUT_CSV = "data/demo_upload.csv"

EXPECTED_REJECTED_RULES = ["RULE_1_UTILIZATION", "RULE_2_AMOUNT", "RULE_5_DATE"]


def build_demo_rows(df: pd.DataFrame) -> list[dict]:
    """
    Build 3 invalid demo rows from a copy of df's first row, each with a new
    Transaction_ID and exactly one validation defect:
      - DEMO001: Budget_Utilization_Percentage = 150  -> RULE_1_UTILIZATION
      - DEMO002: Transaction_Amount = -500             -> RULE_2_AMOUNT
      - DEMO003: Transaction_Date in a different month
                 than Fiscal_Month, same year           -> RULE_5_DATE
    """
    template = df.iloc[0].to_dict()

    utilization_defect = dict(template)
    utilization_defect["Transaction_ID"] = "DEMO001"
    utilization_defect["Budget_Utilization_Percentage"] = 150

    amount_defect = dict(template)
    amount_defect["Transaction_ID"] = "DEMO002"
    amount_defect["Transaction_Amount"] = -500

    fiscal_year = int(template["Fiscal_Year"])
    fiscal_month = int(template["Fiscal_Month"])
    wrong_month = fiscal_month + 1 if fiscal_month < 12 else fiscal_month - 1
    date_defect = dict(template)
    date_defect["Transaction_ID"] = "DEMO003"
    date_defect["Transaction_Date"] = f"{fiscal_year}-{wrong_month:02d}-10"

    return [utilization_defect, amount_defect, date_defect]


def main() -> None:
    df = pd.read_csv(SOURCE_CSV)

    demo_rows = build_demo_rows(df)
    demo_df = pd.concat([df, pd.DataFrame(demo_rows)], ignore_index=True)
    demo_df = demo_df[df.columns.tolist()]
    demo_df.to_csv(OUTPUT_CSV, index=False)

    print(
        f"Wrote {len(demo_df)} rows ({len(df)} original + {len(demo_rows)} invalid) "
        f"to {OUTPUT_CSV}"
    )

    result = validate_csv(OUTPUT_CSV)
    print(f"valid_count={result['valid_count']}")
    print(f"rejected_count={result['rejected_count']}")
    for entry in result["rejected_rows"]:
        print(f"  {entry}")

    rejected_rules = [entry["rule"] for entry in result["rejected_rows"]]
    if result["rejected_count"] != 3 or sorted(rejected_rules) != sorted(EXPECTED_REJECTED_RULES):
        raise SystemExit(
            f"Expected exactly 3 rejected rows with rules {EXPECTED_REJECTED_RULES}, "
            f"got {result['rejected_count']} rejected with rules {rejected_rules}"
        )

    print("OK: demo_upload.csv rejects exactly 3 rows with the expected rules.")


if __name__ == "__main__":
    main()
