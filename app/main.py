from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.routers import health, auth, users, ingest, departments, transactions, analytics, reporting, anomaly, forecasts

logger = get_logger(__name__)

OPENAPI_TAGS = [
    {"name": "auth", "description": "Authentication and JWT access token issuance."},
    {"name": "users", "description": "User account management. Admin only."},
    {"name": "ingest", "description": "Bulk CSV ingestion of expenditure transactions."},
    {"name": "departments", "description": "Department and budget management."},
    {"name": "transactions", "description": "Expenditure transaction creation and lookup."},
    {"name": "analytics", "description": "Budget utilization, variance, and growth-rate analytics."},
    {"name": "reporting", "description": "Annual department trend summary reporting."},
    {"name": "anomaly", "description": "Isolation Forest anomaly detection over expenditure transactions."},
    {"name": "forecasts", "description": "Linear Regression expenditure forecasting."},
]

app = FastAPI(
    title="Financial Analytics System",
    version="1.0.0",
    description=(
        "Budget monitoring, expenditure analytics, anomaly detection, and "
        "expenditure forecasting API for resource-constrained universities."
    ),
    contact={
        "name": "Andrew Karanja Gathirwa",
        "email": "167144@strathmore.edu",
    },
    openapi_tags=OPENAPI_TAGS,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors()), "error_type": "validation_error"},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred.", "error_type": "database_error"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.critical("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred.", "error_type": "internal_error"},
    )


# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
#possible usage in data sources in powerbiRS
#rerout dsn to match correct tables

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(departments.router, tags=["departments"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(reporting.router, prefix="/reporting", tags=["reporting"])
app.include_router(anomaly.router, prefix="/anomaly", tags=["anomaly"])
app.include_router(forecasts.router, prefix="/forecasts", tags=["forecasts"])


@app.get("/")
def root():
    """Root endpoint that returns API information."""
    return {
        "message": "Financial Analytics System API",
        "version": "1.0.0"
    }
