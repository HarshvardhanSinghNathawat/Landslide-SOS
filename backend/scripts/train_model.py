#!/usr/bin/env python
"""Train the Phase 2b risk model on the landslide inventory.

Run from backend/:
    python scripts/train_model.py [--model random_forest|xgboost] [--version 2026.09.15]

This:
  1. builds a balanced dataset (atlas events = positive, ambient points = negatives),
  2. trains XGBoost (default) or RandomForest,
  3. evaluates on a stratified holdout (accuracy/precision/recall/f1/roc_auc/CM),
  4. persists the model + metrics (backend/models/),
  5. records a ModelRun row (served by /admin/model/performance),
  6. scores every zone and writes initial RiskScore rows + Zone.risk_level.

After this, run `python scripts/recompute_risk.py` (or start the Celery beat)
to keep risk refreshed every 30 minutes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import json

from app.config import settings
from app.database import SessionLocal
from app.services.model.trainer import (
    MODEL_PATH,
    train,
    score_all_zones,
    latest_metrics,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train landslide risk model")
    parser.add_argument("--model", choices=["xgboost", "random_forest"], default="xgboost")
    parser.add_argument("--version", default=settings.MODEL_VERSION)
    parser.add_argument("--no-score", action="store_true",
                        help="skip per-zone scoring after training")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        metrics = train(db, model_type=args.model, version=args.version)

        logger.info(json.dumps(metrics, indent=2))
        logger.info("Model saved to: %s", MODEL_PATH)

        if not args.no_score:
            results = score_all_zones(db)
            logger.info("\nPer-zone risk (fused with live SWI):")
            for r in results:
                logger.info(
                    "  %-22s prob=%.3f  level=%s",
                    r["name"], r["probability"], r["level"],
                )
        logger.info("\nLatest model run persisted (see /admin/model/performance).")
    finally:
        db.close()


if __name__ == "__main__":
    main()