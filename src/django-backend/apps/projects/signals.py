from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from api.tasks.web_ui import revalidate_project

if TYPE_CHECKING:
    from apps.projects.models import Project

logger = logging.getLogger(__name__)


def on_project_saved(sender: type, instance: Project, **kwargs: Any) -> None:
    try:
        revalidate_project.enqueue(str(instance.id))
    except Exception:
        logger.exception("Failed to enqueue revalidation for project %s", instance.id)


def on_project_deleted(sender: type, instance: Project, **kwargs: Any) -> None:
    try:
        revalidate_project.enqueue(str(instance.id))
    except Exception:
        logger.exception("Failed to enqueue revalidation for project %s", instance.id)
