"""Production-ready config with security gates.

Settings are validated on import.  If ENVIRONMENT=production and any insecure
default is still in place, the app refuses to start.
"""

from __future__ import annotations

import logging
import sys

from app.config import Settings  # re-export for type-checkers

logger = logging.getLogger("app.startup")

_PROD_INSECURE_DEFAULTS: list[tuple[str, object, str]] = [
    (
        "SECRET_KEY",
        "dev-only-change-me-in-prod-0123456789abcdef",
        "SECRET_KEY must be overridden in production (>=32 chars, random).",
    ),
    (
        "AUTO_CREATE_TABLES",
        True,
        "AUTO_CREATE_TABLES must be False in production — use alembic migrate.",
    ),
    (
        "CORS_ALLOW_ALL",
        True,
        "CORS_ALLOW_ALL must be False in production — restrict CORS_ORIGINS.",
    ),
]


def validate_production_settings(settings: Settings) -> None:
    """Abort the process if a production deployment has insecure defaults."""
    if settings.ENVIRONMENT != "production":
        return

    errors: list[str] = []
    for name, insecure_default, msg in _PROD_INSECURE_DEFAULTS:
        current = getattr(settings, name, None)
        if current == insecure_default:
            errors.append(msg)

    if settings.DEBUG:
        errors.append("DEBUG must be False in production.")

    if errors:
        for e in errors:
            logger.critical("PROD CONFIG: %s", e)
        sys.exit("Aborting: production configuration is insecure. See logs above.")
