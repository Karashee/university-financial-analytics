"""CSV bulk ingestion endpoint."""
import os
import tempfile

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.rbac import finance_or_admin
from app.database import get_db
from app.services.ingestion import ingest_csv

router = APIRouter()


@router.post("/csv", dependencies=[finance_or_admin])
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Bulk ingest a CSV file of expenditure transactions.

    Requires finance_officer or admin role.
    """
    suffix = os.path.splitext(file.filename or "")[1] or ".csv"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(tmp_fd, "wb") as tmp_file:
            tmp_file.write(file.file.read())
        result = ingest_csv(db, tmp_path)
    finally:
        os.remove(tmp_path)
    return result
