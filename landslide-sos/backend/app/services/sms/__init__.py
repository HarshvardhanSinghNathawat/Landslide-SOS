"""SMS provider abstraction — mock / MSG91 / Fast2SMS.

Usage:
    from app.services.sms import send_sms

    result = send_sms(phone="+919876543210", message="Alert: ...")
    print(result.ok, result.provider, result.external_id)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SmsResult:
    ok: bool
    provider: str
    external_id: str | None = None
    error: str | None = None
    raw: dict = field(default_factory=dict)


class SmsProvider(Protocol):
    def send(self, phone: str, message: str, *, template_id: str | None = None) -> SmsResult: ...


class MockProvider:
    """Logs SMS to console — dev/test default."""

    provider = "mock"

    def send(self, phone: str, message: str, *, template_id: str | None = None) -> SmsResult:
        logger.info("[SMS MOCK] %s -> %s", phone, message)
        return SmsResult(ok=True, provider="mock", external_id="mock-000")


class MSG91Provider:
    """MSG91 transactional SMS via REST API (TRAI DLT compliant)."""

    provider = "msg91"

    def __init__(self) -> None:
        import httpx

        self._client = httpx.Client(timeout=30)
        self._auth_key = settings.MSG91_AUTH_KEY
        self._sender_id = settings.MSG91_SENDER_ID
        self._base_url = "https://api.msg91.com/api/v5/flow"

    def send(self, phone: str, message: str, *, template_id: str | None = None) -> SmsResult:
        tid = template_id or settings.MSG91_TEMPLATE_ID
        if not self._auth_key:
            return SmsResult(ok=False, provider="msg91", error="MSG91_AUTH_KEY not configured")

        # Normalise to 10-digit Indian number (strip +91 / 91 prefix)
        import re
        clean = re.sub(r"^\+?91", "", phone).strip()

        payload = {
            "integration": "flow",
            "flow_id": tid,
            "mobiles": f"91{clean}",
            "var": {"message": message},
        }
        headers = {
            "authkey": self._auth_key,
            "Content-Type": "application/json",
        }

        try:
            resp = self._client.post(self._base_url, json=payload, headers=headers)
            data = resp.json()
            ok = resp.status_code == 200 and data.get("type") == "success"
            ext_id = data.get("request_id")
            return SmsResult(
                ok=ok,
                provider="msg91",
                external_id=str(ext_id) if ext_id else None,
                error=None if ok else str(data),
                raw=data,
            )
        except Exception as exc:
            logger.exception("MSG91 send failed")
            return SmsResult(ok=False, provider="msg91", error=str(exc))


def _get_provider() -> SmsProvider:
    name = settings.SMS_PROVIDER.lower()
    if name == "msg91":
        return MSG91Provider()
    return MockProvider()


def send_sms(phone: str, message: str, *, template_id: str | None = None) -> SmsResult:
    """Dispatch an SMS via the configured provider. Returns SmsResult."""
    provider = _get_provider()
    return provider.send(phone, message, template_id=template_id)
