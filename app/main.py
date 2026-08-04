from fastapi import FastAPI
from app.routers import health, auth

app = FastAPI(
    title="Financial Analytics System",
    version="1.0.0"
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/")
def root():
    """Root endpoint that returns API information."""
    return {
        "message": "Financial Analytics System API",
        "version": "1.0.0"
    }
