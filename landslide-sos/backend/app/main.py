from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 — ensure all models registered on Base.metadata
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import admin, alerts, auth, dashboard, rainfall, reports, system, zones
from app.startup import validate_production_settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app.startup")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_production_settings(settings)
    logger.info("LandslideSOS starting (env=%s, debug=%s)", settings.ENVIRONMENT, settings.DEBUG)
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
    yield
    logger.info("LandslideSOS shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

api_prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=api_prefix)
app.include_router(zones.router, prefix=api_prefix)
app.include_router(rainfall.router, prefix=api_prefix)
app.include_router(alerts.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)
app.include_router(system.router, prefix=api_prefix)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": settings.APP_NAME, "version": "0.1.0", "docs": "/docs"}
