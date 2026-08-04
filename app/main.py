from fastapi import FastAPI
from app.routers import health

app = FastAPI(
    title="Financial Analytics System",
    version="1.0.0"
)

# Include routers
app.include_router(health.router)


@app.get("/")
def root():
    """Root endpoint that returns API information."""
    return {
        "message": "Financial Analytics System API",
        "version": "1.0.0"
    }
