from fastapi import APIRouter

from app.config import settings
from app.database import engine
from app.schemas.system import ComponentHealth, HealthOut
from app.services.inventory.loader import count_inventory
from app.services.model.trainer import model_exists
from sqlalchemy import text

router = APIRouter(prefix="/system", tags=["system"])

_COMPONENT_CHECKS: dict[str, dict[str, str | None]] = {
    "Rainfall API (IMD)": {
        "operational": "config=True",
        "degraded": "IMD_API_KEY not set — ingest off (requires IP whitelisting)",
        "url": "api.imd.gov.in/api/v1/aws_data",
    },
    "DEM Processing (SRTM 30m)": {
        "operational": "config=True",
        "degraded": "no API key — unauthenticated, rate-limited (offline cache active)",
        "url": "api.opentopography.org/v1/globaldem",
    },
    "SWI Engine (3-tank)": {
        "operational": "computed from rainfall history",
    },
    "Landslide Inventory": {
        "operational": "events loaded ({} count)",
        "degraded": "no events in DB — run scripts/load_inventory.py",
    },
    "ML Prediction Model": {
        "operational": "model trained ({} model)",
        "degraded": "no model yet — run scripts/train_model.py",
    },
    "Risk Scheduler (Celery)": {
        "operational": "30-min beat configured",
        "degraded": "start with app/tasks/beat worker",
    },
    "SMS Gateway": {
        "operational": "config=True",
        "degraded": "Using mock mode (swap SMS_PROVIDER to 'msg91' for live)",
    },
    "PWA Push Service": {
        "pending": "Phase 3 wires pywebpush",
    },
    "GIS Tile Server": {
        "pending": "Phase 4 Docker compose (TileServer GL)",
    },
}


def _check_db_status() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return "ok"
    except Exception:
        return "error"


def _resolve_status(name: str, db) -> tuple[str, str | None]:
    """Return (status, latency-or-note) for a component."""
    info = _COMPONENT_CHECKS[name]
    if info.get("pending"):
        return "pending", None

    if name == "Rainfall API (IMD)":
        return ("operational" if settings.IMD_API_KEY else "degraded"), None

    if name == "DEM Processing (SRTM 30m)":
        return ("operational" if settings.OPENTOPOGRAPHY_API_KEY else "degraded"), None

    if name == "SWI Engine (3-tank)":
        return "operational", None

    if name == "ML Prediction Model":
        return ("operational" if model_exists() else "degraded"), None

    if name == "Risk Scheduler (Celery)":
        return "operational", None

    if name == "Landslide Inventory":
        try:
            return ("operational" if count_inventory(db) > 0 else "degraded"), None
        except Exception:
            return "degraded", None

    if name == "SMS Gateway":
        return (
            "operational" if settings.SMS_PROVIDER != "mock" else "degraded"
        ), None

    return "operational", None


@router.get("/health", response_model=HealthOut)
def system_health() -> HealthOut:
    from app.database import SessionLocal

    db_status = _check_db_status()
    db = SessionLocal()
    try:
        components: list[ComponentHealth] = []
        for name, info in _COMPONENT_CHECKS.items():
            status_val, _ = _resolve_status(name, db)
            components.append(
                ComponentHealth(
                    name=name,
                    status=status_val,
                    uptime=None,
                    latency=None,
                )
            )
    finally:
        db.close()

    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        components=components,
    )


@router.post("/pipeline/trigger")
def trigger_pipeline() -> dict:
    from app.tasks.rainfall_tasks import ingest_imd
    from app.tasks.risk_tasks import recompute_all

    rainfall_res = ingest_imd()
    risk_res = recompute_all()
    return {
        "status": "ok",
        "rainfall": rainfall_res,
        "zones_scored": len(risk_res),
        "results": risk_res,
    }