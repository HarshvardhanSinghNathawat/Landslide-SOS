"""Celery task: hourly IMD rainfall ingest (no-op until IMD_API_KEY is set)."""

import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.rainfall import RainfallReading
from app.models.zone import Zone
from app.services.rainfall.imd_client import (
    IMDError,
    IMDNotConfigured,
    fetch_zone_rainfall,
)

logger = logging.getLogger(__name__)


@shared_task(name="rainfall.ingest_imd")
def ingest_imd() -> dict:
    """Upsert the latest AWS 24h rainfall for each zone.

    Without IMD_API_KEY the IMD client returns simulated readings (SIM-*
    stations) so the pipeline stays demonstrable; with a real key it fetches
    live AWS station data.
    """
    result = {"updated": 0, "skipped": 0, "reason": None}

    if not settings.IMD_API_KEY:
        result["reason"] = "IMD_API_KEY not set — SIMULATED readings"

    db = SessionLocal()
    try:
        zones = db.scalars(select(Zone)).all()
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        for zone in zones:
            try:
                data = fetch_zone_rainfall(zone.lat, zone.lng)
            except (IMDNotConfigured, IMDError) as exc:
                logger.warning("IMD fetch failed for %s: %s", zone.name, exc)
                result["skipped"] += 1
                continue

            mm = data.get("last_24h_mm", 0.0)
            existing = db.scalar(
                select(RainfallReading).where(
                    RainfallReading.zone_id == zone.id,
                    RainfallReading.timestamp == now,
                )
            )
            if existing:
                existing.observed_mm = mm
            else:
                db.add(RainfallReading(
                    zone_id=zone.id,
                    timestamp=now,
                    observed_mm=mm,
                    forecast_mm=None,
                ))
            result["updated"] += 1
        db.commit()
    finally:
        db.close()
    return result