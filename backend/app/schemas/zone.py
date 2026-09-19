from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    district: str | None = None
    state: str | None = None
    lat: float
    lng: float
    slope: float | None = None
    aspect: float | None = None
    elevation: float | None = None
    lithology: str | None = None
    risk: RiskLevel
    risk_probability: float | None = None
    rainfall: float | None = None
    swi: float | None = None
    last_updated: datetime