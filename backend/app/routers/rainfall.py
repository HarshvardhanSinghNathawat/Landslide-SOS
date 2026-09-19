from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.middleware.auth import DbDep
from app.models.rainfall import RainfallReading
from app.schemas.rainfall import RainfallPoint, RainfallSeries
from sqlalchemy import select

router = APIRouter(prefix="/rainfall", tags=["rainfall"])


def _build_points(readings: list[RainfallReading], hours: int) -> list[RainfallPoint]:
    buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"value": 0.0, "forecast": 0.0})
    for r in readings:
        key = r.timestamp.strftime("%H:00")
        buckets[key]["value"] += r.observed_mm
        if r.forecast_mm is not None:
            buckets[key]["forecast"] += r.forecast_mm

    points: list[RainfallPoint] = []
    for key in sorted(buckets.keys()):
        points.append(
            RainfallPoint(
                time=key,
                value=round(buckets[key]["value"], 2) if buckets[key]["value"] > 0 else None,
                forecast=round(buckets[key]["forecast"], 2) if buckets[key]["forecast"] > 0 else None,
            )
        )
    return points


@router.get("", response_model=RainfallSeries)
def get_rainfall(
    db: DbDep,
    zone_id: int | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
) -> RainfallSeries:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = select(RainfallReading).where(RainfallReading.timestamp >= since)
    if zone_id is not None:
        stmt = stmt.where(RainfallReading.zone_id == zone_id)
    readings = list(db.scalars(stmt.order_by(RainfallReading.timestamp.asc())).all())
    points = _build_points(readings, hours)
    return RainfallSeries(zone_id=zone_id, points=points)