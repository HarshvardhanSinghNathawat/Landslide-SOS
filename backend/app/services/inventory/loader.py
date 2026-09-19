"""ISRO/NRSC Landslide Atlas inventory loader.

Ingests a CSV of landslide events (latitude, longitude, state, district,
event_date, area_ha, severity, trigger) into the `landslide_events` table
for use as training labels in Phase 2b.

The loader is idempotent: duplicate rows (same lat+lng+event_date) are
skipped.  The sample dataset ships at:
    backend/data/inventory/landslide_atlas_sample.csv
"""

from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.landslide import LandslideEvent
from app.services.geo import point_wkt

logger = logging.getLogger(__name__)


def _parse_date(val: str) -> date | None:
    """Try common date formats found in ISRO/NRSC exports."""
    from datetime import datetime

    val = val.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return default


def load_inventory_csv(
    db: Session,
    csv_path: str | Path,
    source_tag: str = "NRSC-ISRO-LandslideAtlas2023",
    *,
    overwrite_geom: bool = False,
) -> dict[str, int]:
    """Load landslide events from a CSV.

    Expected columns (case-insensitive, header row required):
        latitude, longitude, state, district, event_date, area_ha, severity, trigger

    Returns {"loaded": N, "skipped": M}.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Inventory CSV not found: {csv_path}")

    loaded = skipped = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        # Normalise header names
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header row: {csv_path}")
        field_map = {f.strip().lower().replace(" ", "_"): f for f in reader.fieldnames}

        def get(row: dict, key: str) -> str:
            col = field_map.get(key, key)
            return str(row.get(col, "")).strip()

        for row_num, row in enumerate(reader, start=2):
            lat = _to_float(get(row, "latitude"))
            lng = _to_float(get(row, "longitude"))
            if lat == 0.0 or lng == 0.0:
                skipped += 1
                continue

            event_date = _parse_date(get(row, "event_date"))

            # Check for duplicate
            if event_date:
                exists = db.scalar(
                    select(func.count())
                    .select_from(LandslideEvent)
                    .where(
                        LandslideEvent.lat == lat,
                        LandslideEvent.lng == lng,
                        LandslideEvent.event_date == event_date,
                    )
                )
                if exists and exists > 0:
                    skipped += 1
                    continue

            evt = LandslideEvent(
                lat=lat,
                lng=lng,
                state=get(row, "state") or None,
                district=get(row, "district") or None,
                event_date=event_date,
                area_ha=_to_float(get(row, "area_ha")),
                severity=_to_float(get(row, "severity")),
                source=source_tag,
            )

            if overwrite_geom:
                evt.geom_wkt = point_wkt(lng, lat)

            db.add(evt)
            loaded += 1

            if loaded % 500 == 0:
                db.flush()
                logger.info("Loaded %d events so far (row %d)...", loaded, row_num)

    db.commit()
    logger.info("Inventory load complete: %d loaded, %d skipped", loaded, skipped)
    return {"loaded": loaded, "skipped": skipped}


def count_inventory(db: Session) -> int:
    """Count total landslide events in the DB."""
    return db.scalar(select(func.count()).select_from(LandslideEvent)) or 0