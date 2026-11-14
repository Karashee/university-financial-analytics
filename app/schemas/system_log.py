from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SystemLogRead(BaseModel):
    id: int
    logged_at: datetime
    level: str
    logger_name: str
    message: str

    model_config = ConfigDict(from_attributes=True)
