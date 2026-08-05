from fastapi import FastAPI
from app.routers import health, auth, users, ingest, departments, transactions

app = FastAPI(
    title="Financial Analytics System",
    version="1.0.0"
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(departments.router, tags=["departments"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])


@app.get("/")
def root():
    """Root endpoint that returns API information."""
    return {
        "message": "Financial Analytics System API",
        "version": "1.0.0"
    }
