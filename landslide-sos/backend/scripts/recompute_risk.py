#!/usr/bin/env python
"""One-shot: recompute risk for all zones (same logic the Celery beat runs).

Run from backend/:
    python scripts/recompute_risk.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from app.database import SessionLocal
from app.services.model.trainer import ModelNotTrained, score_all_zones

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        try:
            results = score_all_zones(db)
        except ModelNotTrained as exc:
            logger.error("Could not recompute: %s", exc)
            sys.exit(1)
        logger.info("Recomputed risk for %d zones:", len(results))
        for r in results:
            logger.info("  %-22s prob=%.3f  level=%s", r["name"], r["probability"], r["level"])
    finally:
        db.close()


if __name__ == "__main__":
    main()