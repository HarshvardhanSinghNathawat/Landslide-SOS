from pydantic import BaseModel


class RainfallPoint(BaseModel):
    time: str
    value: float | None
    forecast: float | None


class RainfallSeries(BaseModel):
    zone_id: int | None = None
    points: list[RainfallPoint]