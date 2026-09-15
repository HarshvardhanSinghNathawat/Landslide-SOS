from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AlertKind, AlertStatus, RiskLevel


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref: str
    zone_id: int
    zone: str
    type: str
    level: RiskLevel
    kind: AlertKind
    status: AlertStatus
    message: str | None = None
    sms: int
    sms_failed: int
    recipients: int
    time: datetime
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None


class SOSCreate(BaseModel):
    zone_id: int
    kind: AlertKind = AlertKind.landslide
    message: str | None = Field(default=None, max_length=500)


class AlertAcknowledge(BaseModel):
    note: str | None = Field(default=None, max_length=500)