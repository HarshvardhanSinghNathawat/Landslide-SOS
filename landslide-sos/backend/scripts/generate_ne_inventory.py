#!/usr/bin/env python
"""Generate the North-East landslide inventory CSV.

Keeps the genuine Meghalaya rows from the existing Atlantic sample and adds a
deterministic synthetic cluster of events around each Assam / Manipur / Mizoram
monitoring zone so the model trains on regionally coherent data.

Usage (from backend/):
    python scripts/generate_ne_inventory.py
    --> data/inventory/landslide_atlas_ne.csv
"""

import os
import pathlib
import random

OUT_CSV = os.path.join("data", "inventory", "landslide_atlas_ne.csv")
SRC_CSV = os.path.join("data", "inventory", "landslide_atlas_sample.csv")

HEADER = "latitude,longitude,state,district,event_date,area_ha,severity,trigger"

# (lat, lng, district, state, n_events, seed) -- clusters tuned to district relief
CLUSTERS = [
    (25.1647, 93.0188, "Dima Hasao",       "Assam",     60,  101),
    (25.84,   93.43,    "Karbi Anglong",    "Assam",     42,  202),
    (24.82,   92.80,    "Cachar",           "Assam",     30,  303),
    (24.68,   92.56,    "Hailakandi",       "Assam",     20,  404),
    (24.87,   92.36,    "Karimganj",        "Assam",     20,  505),
    (26.50,   93.90,    "Golaghat",         "Assam",     26,  606),
    (23.73,   92.72,    "Aizawl",           "Mizoram",   52,  707),
    (24.33,   93.68,    "Churachandpur",    "Manipur",   34,  808),
    (25.10,   94.37,    "Ukhrul",           "Manipur",   36,  909),
]

YEARS = range(1998, 2023)


def _make_rows() -> list[list[str]]:
    rows: list[list[str]] = []

    # Keep genuine Meghalaya events from the existing sample.
    src = pathlib.Path(SRC_CSV)
    if src.exists():
        with src.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("latitude"):
                    continue
                if "Meghalaya" in line:
                    rows.append(line.split(","))

    # Deterministic synthetic clusters around each monitoring zone.
    for lat, lng, district, state, n, seed in CLUSTERS:
        rng = random.Random(seed)
        for _ in range(n):
            ev_lat = round(lat + rng.uniform(-0.045, 0.045), 5)
            ev_lng = round(lng + rng.uniform(-0.045, 0.045), 5)
            year = rng.choice(list(YEARS))
            month = rng.choice([5, 6, 6, 7, 7, 7, 8, 8, 9, 9, 10])
            day = rng.randint(1, 28)
            area_ha = round(rng.uniform(0.5, 55.0), 2)
            severity = round(rng.uniform(0.05, 0.65), 4)
            rows.append([
                f"{ev_lat:.5f}", f"{ev_lng:.5f}", state, district,
                f"{year:04d}-{month:02d}-{day:02d}",
                f"{area_ha:.2f}", f"{severity:.4f}", "monsoon",
            ])

    return rows


def main() -> None:
    rows = _make_rows()
    out = pathlib.Path(OUT_CSV)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        fh.write(HEADER + "\n")
        for row in rows:
            fh.write(",".join(row) + "\n")

    counts: dict[str, int] = {}
    for row in rows:
        key = row[2] + "|" + row[3]
        counts[key] = counts.get(key, 0) + 1
    print(f"Wrote {len(rows)} events -> {OUT_CSV}")
    for key in sorted(counts):
        print(f"   {key:<34} {counts[key]:>4}")


if __name__ == "__main__":
    main()