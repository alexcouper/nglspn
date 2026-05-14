from typing import Any

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def auto_follow_house_project(
    sender: Any,
    instance: Any,
    created: bool,  # noqa: FBT001
    **kwargs: Any,
) -> None:
    if not created or instance.is_system_user:
        return
    # Local import: apps.follows depends on apps.users via AUTH_USER_MODEL FKs,
    # so deferring the import avoids any import-order pitfalls.
    from apps.follows.services import create_house_project_follow  # noqa: PLC0415

    create_house_project_follow(instance)
