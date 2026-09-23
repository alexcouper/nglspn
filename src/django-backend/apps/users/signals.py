from typing import Any

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.projects.models import OrphanedStorageObject
from apps.users.models import UserAvatar


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


# Same contract as the `ProjectImage` receiver in `apps/projects/signals.py`:
# every way an avatar row can go — replace, remove, the sweep reaping a stale
# reservation, an account being deleted — records its key here, and the
# images sweep deletes the object out of the request path. `pre_delete` so the
# key is still readable, and so the tombstone shares the deletion transaction.
@receiver(pre_delete, sender=UserAvatar)
def record_orphaned_avatar_object(
    sender: Any, instance: UserAvatar, **kwargs: Any
) -> None:
    OrphanedStorageObject.objects.get_or_create(storage_key=instance.storage_key)
