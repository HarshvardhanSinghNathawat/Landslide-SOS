"""Training dataset builder for the Phase 2b risk model.

Positive samples come from the ISRO/NRSC-style landslide inventory. Each
event is joined to its nearest monitoring zone (by great-circle distance) and
its static attributes — slope, elevation, aspect, lithology — plus distance to
that zone. Negative (ambient / no-landslide) samples are drawn deterministically
around the same zone centroids so the classifier learns terrain differences
rather than geography.
"""

from __future__ import annotations

import math

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.landslide import LandslideEvent
from app.models.zone import Zone
from app.services.geo import haversine_m

FEATURE_NAMES = [
    "slope_deg",
    "elevation_m",
    "aspect_sin",
    "aspect_cos",
    "lithology_ordinal",
    "distance_km",
    "severity",
]

LITHOLOGY_ORDER = [
    "Granite",
    "Basalt",
    "Sandstone",
    "Laterite",
    "Metasediment",
    "Gneiss",
    "Phyllite",
]

_AMBIENT_NEGATIVES_PER_ZONE = 60


def lithology_ordinal(lithology: str | None) -> float:
    """Ordinal encode lithology; unknown maps to the median bucket."""
    if not lithology:
        return float(len(LITHOLOGY_ORDER) // 2)
    try:
        return float(LITHOLOGY_ORDER.index(lithology))
    except ValueError:
        return float(len(LITHOLOGY_ORDER) // 2)


def _feature_row(
    zone: Zone,
    distance_m: float,
    severity: float,
) -> list[float]:
    aspect_rad = math.radians(zone.aspect or 0.0)
    return [
        zone.slope or 0.0,
        zone.elevation or 0.0,
        math.sin(aspect_rad),
        math.cos(aspect_rad),
        lithology_ordinal(zone.lithology),
        round(distance_m / 1000.0, 3),
        severity,
    ]


def nearest_zone(zone: Zone, zones: list[Zone]) -> tuple[Zone, float]:
    best, best_d = zone, float("inf")
    for z in zones:
        d = haversine_m(z.lat, z.lng, zone.lat, zone.lng)
        if d < best_d:
            best_d = d
            best = z
    return best, best_d


def nearest_to_point(lat: float, lng: float, zones: list[Zone]) -> tuple[Zone, float]:
    best, best_d = zones[0], float("inf")
    for z in zones:
        d = haversine_m(lat, lng, z.lat, z.lng)
        if d < best_d:
            best_d = d
            best = z
    return best, best_d


def build_dataset(
    db: Session,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (X, y, feature_names) for model training."""
    events = db.scalars(select(LandslideEvent)).all()
    zones = list(db.scalars(select(Zone)).all())
    if not events or not zones:
        raise ValueError("Need at least one LandslideEvent and one Zone to build a dataset")

    rows: list[list[float]] = []
    labels: list[int] = []

    for evt in events:
        zone, dist = nearest_to_point(evt.lat, evt.lng, zones)
        rows.append(
            _feature_row(
                zone, dist, severity=evt.severity if evt.severity is not None else 0.0
            )
        )
        labels.append(1)

    rng = np.random.default_rng(seed)
    for zone in zones:
        for _ in range(_AMBIENT_NEGATIVES_PER_ZONE):
            lat = zone.lat + rng.normal(0.0, 0.25)
            lng = zone.lng + rng.normal(0.0, 0.25)
            nz, dist = nearest_to_point(lat, lng, zones)
            rows.append(_feature_row(nz, dist, severity=0.0))
            labels.append(0)

    X = np.array(rows, dtype=np.float64)
    y = np.array(labels, dtype=np.int64)
    return X, y, FEATURE_NAMES


def zone_feature_vector(zone: Zone, zones: list[Zone]) -> np.ndarray:
    """Feature vector for predicting a single zone (severity=0)."""
    if len(zones) == 1:
        nz, dist = zone, 0.0
    else:
        nz, dist = nearest_zone(zone, zones)
    row = _feature_row(nz, dist, severity=0.0)
    return np.array([row], dtype=np.float64)