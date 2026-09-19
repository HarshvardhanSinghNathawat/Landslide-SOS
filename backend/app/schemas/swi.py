from datetime import date

from pydantic import BaseModel

from app.models.enums import RiskLevel


class SWIPoint(BaseModel):
    date: date
    swi: float
    risk: RiskLevel


class SWISeries(BaseModel):
    zone_id: int
    points: list[SWIPoint]