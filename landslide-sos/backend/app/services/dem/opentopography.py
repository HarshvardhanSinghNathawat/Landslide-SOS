"""OpenTopography SRTM 30m downloader + slope/aspect/elevation extractor.

Downloads an ASCII ArcGrid tile around a point, computes terrain attributes
using numpy gradient, and returns (elevation_m, slope_deg, aspect_deg) at the
centre pixel. Caches tiles on disk in backend/data/dem/.

API: https://api.opentopography.org/v1/globaldem?demtype=SRTMGL1&...
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path

import numpy as np
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DEM_CACHE_DIR = Path(settings.DATA_DIR) / "dem"
_DEM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_WINDOW_DEG = 0.02  # ±0.01° ≈ 1 km around centre
_GRID_SIZE = 2 * int(_WINDOW_DEG / (1 / 1200)) + 1  # ~73 cells for SRTMGL1

API_URL = "https://api.opentopography.org/v1/globaldem"
OT_API_KEY = ""  # optional, bumped into config below


class DEMError(Exception):
    """Raised when DEM download or parsing fails."""


def _parse_aaigrid(text: str) -> tuple[dict[str, float], np.ndarray]:
    """Parse ASCII ArcGrid header + raster into (header, 2d_array)."""
    header: dict[str, float] = {}
    lines = text.strip().splitlines()
    numeric_start = 0
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].lower() in (
            "ncols", "nrows", "xllcorner", "yllcorner", "cellsize",
            "nodata_value", "nodata",
        ):
            key = parts[0].lower().replace("_", "")
            header[key] = float(parts[1])
            numeric_start = i + 1
        else:
            break

    rows = []
    for line in lines[numeric_start:]:
        vals = line.strip().split()
        if vals:
            rows.append([float(v) for v in vals])

    if not rows:
        raise DEMError("No raster data in AAIGrid response")

    arr = np.array(rows)
    expected_nrows = int(header.get("nrows", arr.shape[0]))
    expected_ncols = int(header.get("ncols", arr.shape[1]))
    if arr.shape != (expected_nrows, expected_ncols):
        raise DEMError(
            f"Grid shape {arr.shape} != header ({expected_nrows}, {expected_ncols})"
        )
    return header, arr


def _compute_terrain(
    arr: np.ndarray, header: dict[str, float], centre_lat: float
) -> tuple[float, float, float]:
    """From a local DEM grid, compute elevation/slope/aspect at centre pixel.

    Returns (elevation_m, slope_deg, aspect_deg).
    aspect_deg: 0=north, 90=east, clockwise (direction of steepest descent).
    """
    cellsize_deg = header.get("cellsize", 1 / 1200)
    nodata = header.get("nodatavalue", -32768)

    nrows, ncols = arr.shape
    ci, cj = nrows // 2, ncols // 2  # centre pixel

    elevation = float(arr[ci, cj])
    if elevation <= nodata:
        raise DEMError(f"Centre pixel is NODATA ({elevation})")

    # Gradient in arc-degrees → convert to metres
    m_per_lat = 111_320.0
    m_per_lng = 111_320.0 * max(math.cos(math.radians(centre_lat)), 1e-6)
    m_per_cell_lat = m_per_lat * cellsize_deg
    m_per_cell_lng = m_per_lng * cellsize_deg

    # np.gradient returns [dy, dx] for 2d
    dy_deg, dx_deg = np.gradient(arr, cellsize_deg)
    dz_dx = float(dx_deg[ci, cj]) / m_per_cell_lng  # east positive
    dz_dy = float(dy_deg[ci, cj]) / m_per_cell_lat  # south positive (array row increases south)
    # northward gradient is -dz_dy
    dz_north = -dz_dy

    slope_rad = math.atan(math.sqrt(dz_dx ** 2 + dz_north ** 2))
    slope_deg = math.degrees(slope_rad)

    # Aspect: direction of steepest descent, 0=north, clockwise
    aspect_rad = math.atan2(dz_dx, dz_north)  # atan2(east_component, north_component)
    aspect_deg = math.degrees(aspect_rad) % 360

    return elevation, slope_deg, aspect_deg


def download_srtm_grid(
    north: float, south: float, east: float, west: float
) -> str:
    """Download SRTMGL1 AAIGrid for a bounding box. Caches to disk."""
    cache_key = f"srtmgl1_{north:.4f}_{south:.4f}_{east:.4f}_{west:.4f}.asc"
    cache_path = _DEM_CACHE_DIR / cache_key
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    api_key = getattr(settings, "OPENTOPOGRAPHY_API_KEY", "")
    params: dict[str, str | float] = {
        "demtype": "SRTMGL1",
        "north": round(north, 6),
        "south": round(south, 6),
        "east": round(east, 6),
        "west": round(west, 6),
        "outputFormat": "AAIGrid",
    }
    if api_key:
        params["API_Key"] = api_key

    logger.info(
        "Downloading SRTM grid: N=%s S=%s E=%s W=%s", north, south, east, west
    )
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(API_URL, params=params)
        resp.raise_for_status()

    text = resp.text
    if text.strip().startswith("{"):
        raise DEMError(f"OpenTopography error: {text[:300]}")

    cache_path.write_text(text, encoding="utf-8")
    return text


def fetch_zone_terrain(lat: float, lng: float) -> tuple[float, float, float]:
    """Download SRTM around (lat, lng) and return (elevation, slope, aspect)."""
    half = _WINDOW_DEG / 2
    grid_text = download_srtm_grid(
        north=lat + half,
        south=lat - half,
        east=lng + half,
        west=lng - half,
    )
    header, arr = _parse_aaigrid(grid_text)
    return _compute_terrain(arr, header, lat)