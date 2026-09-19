from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel


class RouteRequest(BaseModel):
    start_lat: float = Field(ge=-90, le=90)
    start_lng: float = Field(ge=-180, le=180)
    end_lat: float = Field(ge=-90, le=90)
    end_lng: float = Field(ge=-180, le=180)


class CrossedZone(BaseModel):
    id: int
    name: str
    risk: RiskLevel


class RoutePath(BaseModel):
    path: list[list[float]]
    km: float
    status: str
    danger_zones: list[CrossedZone] = []


class AvoidedZone(BaseModel):
    id: int
    name: str
    risk: RiskLevel
    lat: float
    lng: float
    district: str | None = None
    state: str | None = None


class RoutePlan(BaseModel):
    start: list[float]
    end: list[float]
    direct: RoutePath
    recommended: RoutePath
    avoided_zones: list[AvoidedZone] = []
    caution_zones: list[AvoidedZone] = []
    timestamp: datetime