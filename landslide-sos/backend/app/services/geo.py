"""Small geographic helpers used across the data pipeline services.

Coordinates are WGS84 decimal degrees; SRID 4326. WKT is the SQLite-safe
representation (real PostGIS `geometry` columns arrive in production via a
Postgres-only migration).
"""

from __future__ import annotations

import math

SRID = 4326
EARTH_RADIUS_M = 6_371_000.0
M_PER_LAT_DEG = 111_320.0


def point_wkt(lng: float, lat: float) -> str:
    """WKT for a point, with longitude first (GeoJSON/PostGIS order)."""
    return f"POINT({lng:.7f} {lat:.7f})"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def meters_per_lng_deg(lat: float) -> float:
    """Metres per degree of longitude at a given latitude."""
    return M_PER_LAT_DEG * max(math.cos(math.radians(lat)), 1e-6)