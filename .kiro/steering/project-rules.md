---
inclusion: always
---
# Financial Analytics System — Project Rules

## Project Purpose
Budget monitoring, expenditure analytics, anomaly detection, and expenditure forecasting
for resource-constrained universities. Stack: Python 3.14, FastAPI, PostgreSQL,
SQLAlchemy 2.x (synchronous), Alembic, pydantic-settings, pandas, scikit-learn, joblib,
python-jose[cryptography], passlib[bcrypt], python-multipart, pytest, httpx.

## Directory Layout
financial_analytics/
├── app/
│   ├── main.py           # App factory, router registration, exception handlers
│   ├── config.py         # pydantic-settings Settings class
│   ├── database.py       # Engine, SessionLocal, get_db()
│   ├── core/             # security.py, auth.py, rbac.py, logging.py
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic v2 schemas
│   ├── routers/          # Thin route handlers only
│   ├── services/         # All business logic and DB queries
│   └── ml/               # Feature engineering, training, scoring
├── alembic/
├── scripts/              # validate_csv.py, seed_data.py, evaluate_models.py
├── tests/unit/
├── tests/integration/
├── saved_models/
├── .env / .env.example
├── requirements.txt
└── README.md

## Non-Negotiable Rules
1. CSV is raw ingestion input only. After POST /ingest/csv, all reads come from PostgreSQL.
2. Power BI connects to PostgreSQL tables/views only. Never to FastAPI. Never to CSV.
3. Never hardcode dataset row counts (2103, 105, or any fixed number) in application code.
4. Routers are thin: parse request, call service, return response. No DB queries in routers.
5. All business logic and SQLAlchemy queries live in services/.
6. ML pipeline order: run Isolation Forest before Linear Regression training.
   LR training always excludes anomaly-flagged records (is_anomaly_ground_truth == 0).
7. budgets is a separate table, keyed by (department_id, fiscal_year).
8. Budget_Allocation from the CSV goes into the budgets table, NOT into expenditure_transactions.
9. Department-head data filtering: admin and finance_officer see all departments.
   department_head sees only rows matching current_user.department_id.
   Implement via a helper: get_dept_filter(current_user) -> str | None
   Returns current_user.department_id if role is ROLE_DEPT_HEAD, else None.
   Routers call this helper and pass the result as dept_id_filter to service functions.
   Service functions filter by department_id when dept_id_filter is not None.
10. Model retraining: always retrain IF and LR on each /anomaly/detect and /forecasts/run
    call. The dataset is small enough that retraining is fast and avoids stale models.
    Save the retrained model after each run (for use by evaluation scripts), but do not
    load from saved_models at the start of a detect/forecast call.

## Role Names — use exactly these strings everywhere
  admin · finance_officer · department_head

## Testing
- Unit tests: pytest, no live DB. Build test data with pd.DataFrame() in code.
- Integration tests (normal): FastAPI TestClient + SQLite override for get_db,
  using SQLITE_TEST_DATABASE_URL from settings. UUID model columns must have a
  Python-side default=uuid4 so SQLite tests work without server_default.
- View tests and Alembic tests: use TEST_DATABASE_URL (a live PostgreSQL test database,
  separate from the development database). Required for Chunks 11, 14, 17.
- Every chunk that adds a function adds at least one test for it.
- After every chunk: pytest passes fully before moving on.

## Chunk Discipline
- Implement ONLY the current chunk.
- Do NOT write placeholder code or stub functions for future chunks.
- End every chunk by summarizing: files changed, commands run, test results, remaining issues.