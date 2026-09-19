"""3-Tank Cascading Reservoir SWI Engine.

Implements a physically-inspired soil water balance model with three
cascading tanks (surface, root-zone, deep sub-surface) fed by daily
rainfall. Output is a normalised Soil Water Index in [0, 1].

References / design rationale
- Cools et al. (2012) "The influence of temporal of soil moisture on
  landslide occurrence" — 3-tank framework applied to landslide early warning.
-TU Wien ASCAT soil moisture product uses exponential filtering with
  comparable time-constants (T1/T2 representation).

The model is purpose-built for the 10 monitoring zones and takes daily
rainfall (mm/day) as input, starting from dry initial conditions.

SWI risk thresholds (matching zones router):
  >= 0.45  →  green   (high moisture → low landslide risk in most terrain)
  >= 0.32  →  yellow
  >= 0.22  →  orange
  <  0.22  →  red     (very dry → steep, unstable slopes)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.models.rainfall import RainfallReading
from app.models.swi import SWIReading
from app.models.zone import Zone


# ── Tank parameters ──────────────────────────────────────────────────────
@dataclass
class SWIParams:
    """3-tank model parameters. Tuned for Indian monsoon-driven landslide terrain."""

    k1: float = 0.60          # surface outflow coefficient (fast drainage)
    k2: float = 0.30          # root-zone outflow coefficient
    k3: float = 0.08          # deep sub-surface recession (slow release)
    link12: float = 0.50      # fraction of surface outflow that percolates to root
    link23: float = 0.70      # fraction of root outflow that percolates to deep
    S1_cap: float = 50.0      # max surface storage (mm)
    S2_cap: float = 120.0     # max root-zone storage (mm)
    S3_cap: float = 300.0     # max deep storage (mm)
    initial_abstraction: float = 2.0  # mm — rainfall below this is lost


_DEFAULT_PARAMS = SWIParams()


# ── Core computation ─────────────────────────────────────────────────────

def daily_from_hourly(
    hourly: list[tuple[datetime, float]],
) -> list[tuple[date, float]]:
    """Aggregate hourly rainfall readings to daily totals (date, mm)."""
    buckets: dict[date, float] = {}
    for ts, mm in hourly:
        day = ts.date() if isinstance(ts, datetime) else ts
        buckets[day] = buckets.get(day, 0.0) + mm
    return sorted(buckets.items())


def compute_swi_series(
    daily_rain_mm: list[float],
    params: SWIParams | None = None,
) -> list[float]:
    """Run the 3-tank model on a daily rainfall series.

    Args:
        daily_rain_mm: list of daily rainfall totals in mm/day.
        params: model parameters (defaults to _DEFAULT_PARAMS).

    Returns:
        list of SWI values (same length as input), one per day.
    """
    p = params or _DEFAULT_PARAMS
    S1 = S2 = S3 = 0.0
    swi_out: list[float] = []

    for rain in daily_rain_mm:
        P_eff = max(0.0, rain - p.initial_abstraction)

        # Surface tank: add input first, then release, then cap
        S1 = S1 + P_eff
        outflow1 = p.k1 * S1
        S1 = max(0.0, min(S1 - outflow1, p.S1_cap))

        # Root-zone tank (fed by surface percolation)
        S2 = S2 + outflow1 * p.link12
        outflow2 = p.k2 * S2
        S2 = max(0.0, min(S2 - outflow2, p.S2_cap))

        # Deep sub-surface tank (fed by root percolation)
        S3 = S3 + outflow2 * p.link23
        outflow3 = p.k3 * S3
        S3 = max(0.0, min(S3 - outflow3, p.S3_cap))

        # Normalise to [0, 1]
        swi = S3 / p.S3_cap
        swi_out.append(round(swi, 4))

    return swi_out


def swi_to_risk_level(swi: float) -> RiskLevel:
    """Map SWI → RiskLevel (thresholds match zones router)."""
    if swi >= 0.45:
        return RiskLevel.green
    if swi >= 0.32:
        return RiskLevel.yellow
    if swi >= 0.22:
        return RiskLevel.orange
    return RiskLevel.red


# ── Database helpers ──────────────────────────────────────────────────────

def aggregate_hourly_to_daily(
    db: Session, zone_id: int, days: int = 45
) -> list[tuple[date, float]]:
    """Pull hourly RainfallReading rows from the DB and aggregate to daily."""
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Move cutoff back N days
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=days)

    stmt = (
        select(RainfallReading.timestamp, RainfallReading.observed_mm)
        .where(RainfallReading.zone_id == zone_id)
        .where(RainfallReading.timestamp >= cutoff)
        .order_by(RainfallReading.timestamp)
    )
    rows = db.execute(stmt).all()
    return daily_from_hourly(rows)


def refresh_zone_swi(db: Session, zone: Zone) -> float:
    """Compute SWI for a zone from its rainfall history, persist results.

    Upserts SWIReading rows (one per day) and updates Zone.swi_current.
    Returns the latest SWI value.
    """
    daily = aggregate_hourly_to_daily(db, zone.id)
    if not daily:
        # Seed the zone's swi_current from mock data (no rainfall yet)
        return zone.swi_current

    rain_series = [mm for _, mm in daily]
    swi_series = compute_swi_series(rain_series)

    now = datetime.now(timezone.utc)
    latest_swi = swi_series[-1] if swi_series else zone.swi_current

    # Upsert one SWIReading per day
    for (day, _rain), swi_val in zip(daily, swi_series):
        ts = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
        existing = db.scalar(
            select(SWIReading).where(
                SWIReading.zone_id == zone.id,
                SWIReading.timestamp == ts,
            )
        )
        if existing:
            existing.computed_swi = swi_val
        else:
            db.add(SWIReading(
                zone_id=zone.id,
                timestamp=ts,
                computed_swi=swi_val,
            ))

    zone.swi_current = latest_swi
    zone.last_updated = now
    db.commit()
    return latest_swi


def refresh_all_zones_swi(db: Session) -> dict[int, float]:
    """Recompute SWI for every zone. Returns {zone_id: latest_swi}."""
    zones = db.scalars(select(Zone)).all()
    results: dict[int, float] = {}
    for zone in zones:
        results[zone.id] = refresh_zone_swi(db, zone)
    return results