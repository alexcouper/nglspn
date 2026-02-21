from __future__ import annotations

import json
import logging
import urllib.request

from django.conf import settings

from services.web_ui.handler_interface import WebUIHandlerInterface

logger = logging.getLogger(__name__)


class DjangoWebUIHandler(WebUIHandlerInterface):
    def revalidate_paths(self, paths: list[str]) -> None:
        secret = settings.REVALIDATION_SECRET
        if not secret:
            logger.debug("REVALIDATION_SECRET not set, skipping revalidation")
            return

        url = f"{settings.FRONTEND_URL}/api/revalidate"
        payload = json.dumps({"secret": secret, "paths": paths}).encode()
        req = urllib.request.Request(  # noqa: S310
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                logger.info(
                    "Revalidation request sent for %s (status %s)",
                    paths,
                    resp.status,
                )
        except Exception:
            logger.exception("Failed to send revalidation request for %s", paths)
