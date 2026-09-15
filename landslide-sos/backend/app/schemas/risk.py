from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RiskLevel


class RiskOut(BaseModel):
    zone_id: int
    probability: float
    level: RiskLevel
    computed_at: datetime
    model_version: str | None = None