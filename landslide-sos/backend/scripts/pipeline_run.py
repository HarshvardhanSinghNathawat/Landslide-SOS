#!/usr/bin/env python
"""One-shot risk pipeline runner: DEM -> rainfall -> SWI -> risk.

Chains the existing building blocks so an operator can refresh every zone's
terrain (OpenTopography SRTM), rainfall (IMD AWS), soil-water index, and fused
risk level in a single deterministic run — the guaranteed path for a demo,
independent of whether Celery beat happens to be running.

Steps (each can be skipped):
  1. DEM        scripts/update_zone_terrain logic (fetch_zone_terrain)
  2. Rainfall   rainfall_tasks.ingest_imd logic (graceful if IMD unreachable)
  3. SWI        swi/engine.refresh_all_zones_swi
  4. Risk       model/trainer.score_all_zones (updates Zone.risk_level + RiskScore)

Run from backend/:
    python scripts/pipeline_run.py [--zone-id 1] [--skip-dem] [--skip-rainfall]
                                   [--skip-swi] [--skip-risk] [--alerts] [--dry-run]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.models.rainfall import RainfallReading  # noqa: E402
from app.models.zone import Zone  # noqa: E402
from app.services.dem.opentopography import DEMError, fetch_zone_terrain  # noqa: E402
from app.services.geo import point_wkt  # noqa: E402
from app.services.model.trainer import ModelNotTrained, score_all_zones  # noqa: E402
from app.services.rainfall.imd_client import (  # noqa: E402
    IMDError,
    IMDNotConfigured,
    fetch_zone_rainfall,
)
from app.services.swi.engine import refresh_all_zones_swi  # noqa: E402
from app.services.model.trainer import load_model  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
engine.echo = False
logger = logging.getLogger(__name__)


def _zones(db, zone_id: int | None) -> list:
    stmt = select(Zone)
    if zone_id:
        stmt = stmt.where(Zone.id == zone_id)
    return list(db.scalars(stmt).all())


def step_dem(db, zones: list, *, dry_run: bool) -> int:
    """Fetch real SRTM terrain per zone (cached under data/dem/)."""
    if dry_run:
        logger.info("  (dry-run) would fetch SRTM terrain for %d zone(s)", len(zones))
        return 0
    ok = 0
    for zone in zones:
        try:
            elevation, slope, aspect = fetch_zone_terrain(zone.lat, zone.lng)
        except (DEMError, Exception) as exc:  # noqa: BLE001
            logger.warning("  %s: DEM failed (%s) — keeping cached values", zone.name, exc)
            continue
        logger.info(
            "  %-22s elev=%7.1fm  slope=%5.1f°  aspect=%5.1f°",
            zone.name, elevation, slope, aspect,
        )
        if dry_run:
            continue
        zone.elevation = round(elevation, 1)
        zone.slope = round(slope, 1)
        zone.aspect = round(aspect, 1)
        zone.geom_wkt = point_wkt(zone.lng, zone.lat)
        ok += 1
    if not dry_run:
        db.commit()
    return ok


def step_rainfall(db, zones: list, *, dry_run: bool) -> int:
    """Upsert nearest IMD AWS station's 24h rainfall per zone (best-effort)."""
    if not settings.IMD_API_KEY:
        logger.warning("  IMD_API_KEY not set — rainfall ingest skipped (using stored history)")
        return 0

    from datetime import datetime, timezone

    if dry_run:
        logger.info("  (dry-run) would fetch IMD AWS rainfall for %d zone(s)", len(zones))
        return 0

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    ok = 0
    for zone in zones:
        try:
            data = fetch_zone_rainfall(zone.lat, zone.lng)
        except (IMDNotConfigured, IMDError) as exc:
            logger.warning("  %s: IMD unavailable (%s) — keeping stored value", zone.name, exc)
            continue

        mm = data.get("last_24h_mm", 0.0)
        logger.info("  %-22s station=%-6s rain=%6.1f mm (d=%6.0fm)",
                    zone.name, data.get("station", "?"), mm, data.get("distance_m", 0))
        if dry_run:
            continue
        existing = db.scalar(
            select(RainfallReading).where(
                RainfallReading.zone_id == zone.id,
                RainfallReading.timestamp == now,
            )
        )
        if existing:
            existing.observed_mm = mm
        else:
            db.add(RainfallReading(zone_id=zone.id, timestamp=now, observed_mm=mm, forecast_mm=None))
        ok += 1
    if not dry_run:
        db.commit()
    return ok


def step_swi(db, zones: list, *, dry_run: bool) -> dict[int, float]:
    """Refresh the 3-tank SWI for all zones from stored rainfall history."""
    if dry_run:
        return {z.id: z.swi_current for z in zones}
    return refresh_all_zones_swi(db)


def step_risk(db, *, dry_run: bool, create_alerts: bool) -> list[dict]:
    """Fused risk score per zone -> Zone.risk_level + RiskScore rows."""
    if dry_run:
        logger.info("  (dry-run) would recompute fused risk for all zones")
        return []
    try:
        results = score_all_zones(db, refresh_swi=False)
    except ModelNotTrained as exc:
        logger.warning("  risk step skipped: %s", exc)
        return []

    logger.info("  recomputed fused risk for %d zones:", len(results))
    for r in results:
        logger.info("  %-22s prob=%.3f  level=%s", r["name"], r["probability"], r["level"])

    if create_alerts:
        from app.tasks.alert_tasks import check_and_create_escalation_alerts

        created = check_and_create_escalation_alerts(db, results)
        logger.info("  created %d escalation alert(s)", len(created))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the risk pipeline (DEM -> rainfall -> SWI -> risk)")
    parser.add_argument("--zone-id", type=int, help="single zone to process (default: all)")
    parser.add_argument("--skip-dem", action="store_true", help="skip terrain refresh")
    parser.add_argument("--skip-rainfall", action="store_true", help="skip IMD rainfall ingest")
    parser.add_argument("--skip-swi", action="store_true", help="skip SWI recompute")
    parser.add_argument("--skip-risk", action="store_true", help="skip fused risk scoring")
    parser.add_argument("--alerts", action="store_true", help="create escalation alerts after risk (needs risk step)")
    parser.add_argument("--dry-run", action="store_true", help="report what would run without writing anything")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        zones = _zones(db, args.zone_id)
        if not zones:
            logger.info("No zones found — run scripts/seed_data.py first")
            return

        logger.info("Pipeline for %d zone(s) (dry_run=%s)  IMD_API_KEY=%s  EMPTY=%s",
                    len(zones), args.dry_run,
                    "set" if settings.IMD_API_KEY else "unset",
                    "N/A")

        if not args.skip_dem:
            logger.info("[1/4] DEM terrain (OpenTopography SRTM 30m)")
            n = step_dem(db, zones, dry_run=args.dry_run)
            logger.info("  updated terrain for %d zone(s)", n)

        if not args.skip_rainfall:
            logger.info("[2/4] IMD rainfall ingest")
            n = step_rainfall(db, zones, dry_run=args.dry_run)
            logger.info("  wrote rainfall for %d zone(s)", n)

        if not args.skip_swi:
            logger.info("[3/4] SWI recompute (3-tank)")
            swi = step_swi(db, zones, dry_run=args.dry_run)
            if args.dry_run:
                logger.info("  (dry-run) would refresh SWI for %d zone(s)", len(swi))

        if not args.skip_risk:
            logger.info("[4/4] Fused risk scoring (model %s)", load_model().get("version", "?") if os.path.exists(os.path.join(settings.MODEL_DIR, "risk_model.joblib")) else "missing")
            step_risk(db, dry_run=args.dry_run, create_alerts=args.alerts)

        logger.info("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()