#!/usr/bin/env python
"""Recompute Soil Water Index (3-tank model) for all zones.

Run from backend/:
    python scripts/compute_swi.py [--days 45]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging

from app.database import SessionLocal
from app.models.zone import Zone
from app.models.enums import RiskLevel
from app.services.swi.engine import refresh_all_zones_swi, swi_to_risk_level
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute SWI for all zones")
    parser.add_argument("--days", type=int, default=45, help="lookback window in days")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        results = refresh_all_zones_swi(db)
        zones = {z.id: z for z in db.scalars(select(Zone)).all()}
        logger.info("SWI recompute complete:")
        for zone_id, swi in sorted(results.items()):
            zone = zones[zone_id]
            level = swi_to_risk_level(swi)
            logger.info("  %-22s SWI=%.4f  risk=%s", zone.name, swi, level.value)
    finally:
        db.close()


if __name__ == "__main__":
    main()