#!/usr/bin/env python
"""Recompute Zone terrain attributes (elevation/slope/aspect) from SRTM 30m.

Downloads an SRTMGL1 (30m) window via OpenTopography around each zone's
coordinates and updates the Zone row. Uses disk cache under data/dem/ so
subsequent runs are offline.

Run from backend/:
    python scripts/update_zone_terrain.py [--zone-id 1] [--force]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import argparse

from sqlalchemy import select

from app.database import SessionLocal
from app.models.zone import Zone
from app.services.dem.opentopography import (
    DEMError,
    fetch_zone_terrain,
)
from app.services.geo import point_wkt

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update zone terrain from SRTM 30m")
    parser.add_argument("--zone-id", type=int, help="single zone to process (default: all)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stmt = select(Zone)
        if args.zone_id:
            stmt = stmt.where(Zone.id == args.zone_id)
        zones = db.scalars(stmt).all()

        if not zones:
            logger.info("No zones to process")
            return

        for zone in zones:
            try:
                elevation, slope, aspect = fetch_zone_terrain(zone.lat, zone.lng)
                zone.elevation = round(elevation, 1)
                zone.slope = round(slope, 1)
                zone.aspect = round(aspect, 1)
                zone.geom_wkt = point_wkt(zone.lng, zone.lat)
                db.commit()
                logger.info(
                    "%-22s elev=%7.1fm  slope=%5.1f°  aspect=%5.1f°  geom=%s",
                    zone.name, elevation, slope, aspect, point_wkt(zone.lng, zone.lat),
                )
            except (DEMError, Exception) as exc:  # noqa: BLE001
                logger.warning("  %s: terrain update failed (%s) — keeping cached values", zone.name, exc)

    finally:
        db.close()


if __name__ == "__main__":
    main()