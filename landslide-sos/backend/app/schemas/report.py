from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus


class ReportCreate(BaseModel):
    zone_id: int
    kind: str = Field(default="visual-confirm", max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class ReportStatusUpdate(BaseModel):
    status: ReportStatus


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zone: str | None = None
    reporter: str | None = None
    zone_id: int
    kind: str
    description: str | None = None
    status: ReportStatus
    created_at: datetime