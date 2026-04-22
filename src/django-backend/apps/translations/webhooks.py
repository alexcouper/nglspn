import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def notify_web_ui(locale: str) -> None:
    """Best-effort POST to the web-ui's revalidation endpoint. Never raises."""
    url = settings.WEB_UI_REVALIDATE_URL
    if not url:
        return
    try:
        requests.post(
            url,
            json={"locale": locale},
            headers={"X-Revalidate-Secret": settings.WEB_UI_REVALIDATE_SECRET},
            timeout=2,
        )
    except Exception as exc:  # noqa: BLE001 - intentional broad catch
        logger.warning("revalidate webhook failed for locale=%s: %s", locale, exc)
