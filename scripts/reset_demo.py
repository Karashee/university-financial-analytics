"""
Demo reset tool for local development.

Empties the tables that accumulate demo/analysis data (transactions, budgets,
computed reports, and the audit log) while keeping roles, users, and
departments intact, since users depend on departments.

Usage:
    python -m scripts.reset_demo --status   # print row counts, change nothing
    python -m scripts.reset_demo --yes      # truncate the reset tables
    python -m scripts.reset_demo            # print usage, change nothing
"""
import argparse
import sys

from sqlalchemy import create_engine, text

from app.config import settings

# Emptied by --yes. No CASCADE needed: the only foreign key among these
# tables is anomaly_results.transaction_id -> expenditure_transactions, and
# both are truncated together in the same statement.
TABLES_TO_RESET = [
    "anomaly_results",
    "forecast_results",
    "budget_utilization_report",
    "trend_summaries",
    "expenditure_transactions",
    "budgets",
    "system_logs",
]

# Never touched by --yes. Users depend on departments.
KEPT_TABLES = ["roles", "users", "departments"]

ALL_STATUS_TABLES = TABLES_TO_RESET + KEPT_TABLES


def get_table_counts(engine, table_names: list[str]) -> dict[str, int]:
    """Return {table_name: row_count} for each table, read-only."""
    counts = {}
    with engine.connect() as conn:
        for table_name in table_names:
            counts[table_name] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()
    return counts


def print_counts(counts: dict[str, int], label: str) -> None:
    print(f"\n{label}")
    width = max(len(name) for name in counts)
    for name, count in counts.items():
        print(f"  {name:<{width}}  {count}")


def truncate_tables(engine, table_names: list[str]) -> None:
    """Empty every listed table in a single TRUNCATE ... RESTART IDENTITY statement, no CASCADE."""
    table_list = ", ".join(table_names)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY"))


def run_status(engine) -> None:
    counts = get_table_counts(engine, ALL_STATUS_TABLES)
    print_counts(counts, "Current row counts:")


def run_reset(engine) -> None:
    before = get_table_counts(engine, ALL_STATUS_TABLES)
    print_counts(before, "Row counts before reset:")

    truncate_tables(engine, TABLES_TO_RESET)

    after = get_table_counts(engine, ALL_STATUS_TABLES)
    print_counts(after, "Row counts after reset:")
    print(
        f"\nReset complete: emptied {len(TABLES_TO_RESET)} tables "
        f"({', '.join(TABLES_TO_RESET)}). Kept {', '.join(KEPT_TABLES)}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reset demo data: empties transactions, budgets, computed reports, "
            "and the audit log. Keeps roles, users, and departments."
        )
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current row counts for all tables. Changes nothing.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Truncate anomaly_results, forecast_results, budget_utilization_report, "
            "trend_summaries, expenditure_transactions, budgets, and system_logs. "
            "Keeps roles, users, and departments."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.status and not args.yes:
        parser.print_help()
        sys.exit(1)

    engine = create_engine(settings.database_url)

    if args.yes:
        run_reset(engine)
    elif args.status:
        run_status(engine)


if __name__ == "__main__":
    main()
