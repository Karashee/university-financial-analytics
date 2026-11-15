"""
End-to-end smoke test against a running server.

Walks the whole demo path the way the web interface does - sign in, upload,
run the four analytical stages, read the audit log, then check that a
department head only sees their own department - and prints a PASS/FAIL line
per check. Exits non-zero if anything fails.

Run with the server already up:
    python -m scripts.smoke_demo
    python -m scripts.smoke_demo --server-url http://localhost:8000

It does not touch the database itself. For a clean run from an empty
database, run `python -m scripts.reset_demo --yes` first.
"""
import argparse
import sys

import httpx

DEMO_CSV = "data/demo_upload.csv"
FORECAST_MONTHS = 3

# FOR LOCAL DEVELOPMENT ONLY - these are the seeded demo users.
FINANCE_USERNAME, FINANCE_PASSWORD = "finance", "Finance@123"
DEPTHEAD_USERNAME, DEPTHEAD_PASSWORD = "depthead", "DeptHead@123"

# data/demo_upload.csv carries exactly three invalid rows, one per rule.
# See scripts/make_demo_csv.py.
EXPECTED_REJECTED_RULES = {"RULE_1_UTILIZATION", "RULE_2_AMOUNT", "RULE_5_DATE"}

# The INFO line each pipeline action writes. Prefixes come from the
# logger.info calls in app/routers/.
PIPELINE_LOG_PREFIXES = [
    "CSV ingested:",
    "Computed budget utilization:",
    "Computed trend summaries:",
    "Anomaly detection run:",
    "Forecast run:",
]

# Model retraining and scoring take a few seconds on the full dataset.
SLOW_CALL_TIMEOUT = 120.0


class Report:
    """Collects PASS/FAIL lines and remembers whether anything failed."""

    def __init__(self) -> None:
        self.failures = 0

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        if not passed:
            self.failures += 1
        suffix = " - " + detail if detail else ""
        print(("PASS  " if passed else "FAIL  ") + name + suffix)
        return passed

    def step(self, title: str) -> None:
        print("")
        print("== " + title + " ==")


def sign_in(client: httpx.Client, username: str, password: str) -> str:
    response = client.post(
        "/auth/token", data={"username": username, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": "Bearer " + token}


def check_ingest(client: httpx.Client, report: Report, headers: dict) -> None:
    report.step("Upload and validate " + DEMO_CSV)

    with open(DEMO_CSV, "rb") as csv_file:
        response = client.post(
            "/ingest/csv",
            headers=headers,
            files={"file": (DEMO_CSV, csv_file, "text/csv")},
            timeout=SLOW_CALL_TIMEOUT,
        )

    if not report.check("POST /ingest/csv returns 200", response.status_code == 200,
                        "got " + str(response.status_code)):
        return

    body = response.json()
    inserted = body["inserted_rows"]
    skipped = body["skipped_rows"]
    rejected = body["rejected_rows"]

    print("      inserted=" + str(inserted) + " skipped=" + str(skipped) +
          " rejected=" + str(len(rejected)))

    # Either a fresh insert or an idempotent re-upload is a healthy result.
    report.check(
        "rows were accepted (inserted or already present)",
        inserted > 0 or skipped > 0,
        "inserted=" + str(inserted) + " skipped=" + str(skipped),
    )
    report.check("exactly 3 rows rejected", len(rejected) == 3,
                 "got " + str(len(rejected)))

    rules = {entry["rule"] for entry in rejected}
    report.check(
        "rejected rules are the three expected",
        rules == EXPECTED_REJECTED_RULES,
        "got " + str(sorted(rules)),
    )
    for entry in rejected:
        print("      rejected " + str(entry["transaction_id"]) + ": " + entry["rule"])


def check_pipeline(client: httpx.Client, report: Report, headers: dict) -> None:
    """Run the four analytical stages in order, as the workspace page does."""
    report.step("Run the four analytical stages in order")

    # 1 - budget utilisation
    response = client.post("/analytics/compute/budget-utilization",
                           headers=headers, timeout=SLOW_CALL_TIMEOUT)
    if report.check("POST /analytics/compute/budget-utilization returns 200",
                    response.status_code == 200, "got " + str(response.status_code)):
        rows = response.json()["rows_written"]
        print("      rows_written=" + str(rows))
        report.check("budget utilisation wrote rows", rows > 0, "rows_written=" + str(rows))

    # 2 - trend summaries
    response = client.post("/reporting/compute/trend-summaries",
                           headers=headers, timeout=SLOW_CALL_TIMEOUT)
    if report.check("POST /reporting/compute/trend-summaries returns 200",
                    response.status_code == 200, "got " + str(response.status_code)):
        rows = response.json()["rows_written"]
        print("      rows_written=" + str(rows))
        report.check("trend summaries wrote rows", rows > 0, "rows_written=" + str(rows))

    # 3 - anomaly detection, before forecasting so flagged rows are excluded
    #     from forecast training
    response = client.post("/anomaly/detect", headers=headers, timeout=SLOW_CALL_TIMEOUT)
    if report.check("POST /anomaly/detect returns 200",
                    response.status_code == 200, "got " + str(response.status_code)):
        body = response.json()
        scored = body["total_scored"]
        flagged = body["flagged_count"]
        print("      total_scored=" + str(scored) + " flagged_count=" + str(flagged) +
              " model_version=" + str(body["model_version"]))
        report.check("every transaction was scored", scored > 0, "total_scored=" + str(scored))
        report.check("flagged count within range", 0 <= flagged <= scored,
                     "flagged=" + str(flagged) + " scored=" + str(scored))
        report.check("model version is IF_v1.0", body["model_version"] == "IF_v1.0",
                     "got " + str(body["model_version"]))

    # 4 - expenditure forecast
    response = client.post("/forecasts/run", params={"n_months": FORECAST_MONTHS},
                           headers=headers, timeout=SLOW_CALL_TIMEOUT)
    if report.check("POST /forecasts/run returns 200",
                    response.status_code == 200, "got " + str(response.status_code)):
        body = response.json()
        total = body["total_forecasts"]
        print("      total_forecasts=" + str(total) +
              " mae_context=" + str(body["mae_context"]) +
              " n_months_ahead=" + str(body["n_months_ahead"]))
        report.check("forecasts were generated", total > 0, "total_forecasts=" + str(total))
        report.check("horizon echoes the request",
                     body["n_months_ahead"] == FORECAST_MONTHS,
                     "got " + str(body["n_months_ahead"]))
        report.check("training MAE is not negative", body["mae_context"] >= 0,
                     "mae_context=" + str(body["mae_context"]))
        # One forecast per department per month, so the total divides evenly.
        report.check("total divides evenly by the horizon",
                     total % FORECAST_MONTHS == 0,
                     "total=" + str(total) + " months=" + str(FORECAST_MONTHS))


def check_audit_log(client: httpx.Client, report: Report, headers: dict) -> None:
    report.step("Audit log records the pipeline actions")

    response = client.get("/logs", params={"limit": 10}, headers=headers)
    if not report.check("GET /logs returns 200", response.status_code == 200,
                        "got " + str(response.status_code)):
        return

    entries = response.json()
    messages = [entry["message"] for entry in entries]
    print("      " + str(len(entries)) + " entries returned")

    for prefix in PIPELINE_LOG_PREFIXES:
        found = any(message.startswith(prefix) for message in messages)
        report.check("log contains " + repr(prefix), found)


def check_department_scope(client: httpx.Client, report: Report) -> None:
    """The server, not the page, restricts a department head to their own rows."""
    report.step("Department head sees only their own department")

    token = sign_in(client, DEPTHEAD_USERNAME, DEPTHEAD_PASSWORD)
    headers = auth(token)

    response = client.get("/auth/me", headers=headers)
    if not report.check("GET /auth/me returns 200", response.status_code == 200,
                        "got " + str(response.status_code)):
        return

    me = response.json()
    department_id = me["department_id"]
    report.check("department head has a department", department_id is not None)
    print("      " + str(me["username"]) + " role=" + str(me["role"]) +
          " department=" + str(department_id) + " (" + str(me["department_name"]) + ")")

    response = client.get("/anomaly/results", headers=headers, timeout=SLOW_CALL_TIMEOUT)
    if report.check("GET /anomaly/results returns 200", response.status_code == 200,
                    "got " + str(response.status_code)):
        rows = response.json()
        others = sorted({row["department_id"] for row in rows} - {department_id})
        print("      " + str(len(rows)) + " anomaly rows visible")
        report.check(
            "every anomaly row belongs to " + str(department_id),
            not others,
            "also saw " + str(others),
        )

    response = client.get("/forecasts", headers=headers, timeout=SLOW_CALL_TIMEOUT)
    if report.check("GET /forecasts returns 200", response.status_code == 200,
                    "got " + str(response.status_code)):
        rows = response.json()
        others = sorted({row["department_id"] for row in rows} - {department_id})
        print("      " + str(len(rows)) + " forecast rows visible")
        report.check(
            "every forecast row belongs to " + str(department_id),
            not others,
            "also saw " + str(others),
        )
        report.check("the department has a forecast", len(rows) > 0,
                     "got " + str(len(rows)) + " rows")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end smoke test against a running server."
    )
    parser.add_argument("--server-url", default="http://localhost:8000",
                        help="Base URL of the running API server.")
    args = parser.parse_args()

    print("Smoke test against " + args.server_url)
    print("This script does not reset the database. For a clean run from an")
    print("empty database, run `python -m scripts.reset_demo --yes` first.")

    report = Report()

    try:
        with httpx.Client(base_url=args.server_url, timeout=30.0) as client:
            report.step("Sign in as the finance officer")
            finance_token = sign_in(client, FINANCE_USERNAME, FINANCE_PASSWORD)
            report.check("finance officer signed in", bool(finance_token))
            finance_headers = auth(finance_token)

            check_ingest(client, report, finance_headers)
            check_pipeline(client, report, finance_headers)
            check_audit_log(client, report, finance_headers)
            check_department_scope(client, report)
    except httpx.HTTPStatusError as error:
        print("")
        print("FAIL  request rejected: " + str(error.request.method) + " " +
              str(error.request.url) + " returned " + str(error.response.status_code))
        sys.exit(1)
    except httpx.RequestError as error:
        print("")
        print("FAIL  could not reach " + args.server_url + ": " + str(error))
        print("      Start the server first: uvicorn app.main:app --reload")
        sys.exit(1)
    except FileNotFoundError as error:
        print("")
        print("FAIL  missing file: " + str(error))
        print("      Generate the demo CSV first: python -m scripts.make_demo_csv")
        sys.exit(1)

    print("")
    if report.failures:
        print("=== SMOKE TEST FAILED: " + str(report.failures) + " check(s) failed ===")
        sys.exit(1)
    print("=== SMOKE TEST PASSED: all checks green ===")


if __name__ == "__main__":
    main()
