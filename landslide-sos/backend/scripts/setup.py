"""One-time setup for fresh clone.

Run from backend/:
    python scripts/setup.py

Does: seed data → load inventory → compute SWI → train model.
Idempotent: safe to run multiple times (uses upsert logic where available).
"""

import subprocess
import sys
from pathlib import Path


def run(cmd: str) -> None:
    print(f"\n{'='*60}\n  {cmd}\n{'='*60}")
    result = subprocess.run(cmd, shell=True, cwd=Path(__file__).resolve().parent.parent)
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode}): {cmd}")
        sys.exit(1)
    print(f"  OK")


def main() -> None:
    # Ensure dependencies are installed
    run(f"{sys.executable} -m pip install -q -r requirements.txt")

    # Seed zones + users
    run(f"{sys.executable} scripts/seed_data.py")

    # Load landslide inventory (841 NRSC/ISRO events)
    run(f"{sys.executable} scripts/load_inventory.py")

    # Compute Slope Wetness Index (uses cached DEM or synthetic fallback)
    run(f"{sys.executable} scripts/compute_swi.py")

    # Train XGBoost risk model + score all zones
    run(f"{sys.executable} scripts/train_model.py")

    print(f"\n{'='*60}")
    print("  SETUP COMPLETE — start the server with:")
    print(f"    cd backend && {sys.executable} -m uvicorn app.main:app --port 8000")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
