#!/usr/bin/env python
"""Load the Landslide Atlas inventory into landmark_events.

Usage (from backend/):
    python scripts/load_inventory.py \
        --csv data/inventory/landslide_atlas_sample.csv \
        --source "NRSC-ISRO Landslide Atlas 2023 (sample derived)"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging

from app.database import SessionLocal
from app.services.inventory.loader import load_inventory_csv, count_inventory

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load landslide inventory CSV")
    parser.add_argument(
        "--csv",
        default=os.path.join("data", "inventory", "landslide_atlas_ne.csv"),
        help="path to inventory CSV",
    )
    parser.add_argument("--source", default="NRSC-ISRO Landslide Atlas 2023 (sample)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = load_inventory_csv(db, args.csv, source_tag=args.source, overwrite_geom=True)
        logger.info("Loaded: %d, skipped: %d", result["loaded"], result["skipped"])
        logger.info("Total events in DB: %d", count_inventory(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()