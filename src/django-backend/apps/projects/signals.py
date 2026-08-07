from typing import Any

from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from apps.projects.models import (
    ImageVariant,
    OrphanedStorageObject,
    Project,
    ProjectContributor,
    ProjectImage,
)

DEFAULT_CHANNEL_NAME = "Updates"


@receiver(post_save, sender=ProjectContributor)
def recompute_on_contributor_save(
    sender: Any, instance: ProjectContributor, **kwargs: Any
) -> None:
    instance.project.recompute_community_tipoff()


@receiver(post_save, sender=Project)
def create_default_channel(
    sender: Any,
    instance: Project,
    created: bool,  # noqa: FBT001
    **kwargs: Any,
) -> None:
    if not created:
        return
    # Local import: the follows app depends on projects, so importing at module
    # load time would create a circular import path through apps/follows/models.
    from apps.follows.models import Channel  # noqa: PLC0415

    Channel.objects.get_or_create(project=instance, name=DEFAULT_CHANNEL_NAME)


@receiver(post_delete, sender=ProjectContributor)
def recompute_on_contributor_delete(
    sender: Any, instance: ProjectContributor, **kwargs: Any
) -> None:
    # During a Project cascade delete, the project row itself may already be
    # gone or about to be removed; recomputing then is both wasteful and
    # potentially racy. Look it up directly rather than via the FK descriptor
    # so a missing row surfaces as DoesNotExist instead of raising mid-write.
    try:
        project = Project.objects.get(pk=instance.project_id)
    except Project.DoesNotExist:
        return
    project.recompute_community_tipoff()


# ----------------------------------------------------------------------
# Storage tombstones
# ----------------------------------------------------------------------
#
# DO NOT REMOVE THESE TWO RECEIVERS, and do not "optimise" them away.
#
# Django's deletion collector fast-deletes cascaded rows with a single
# `DELETE ... WHERE` and no signals, but it only takes that path when the model
# has no `pre_delete`/`post_delete` receiver. Registering these disables
# fast-delete for `ProjectImage` and `ImageVariant`, which is the only reason
# cascades from `Article` and from `Project` record their keys at all — and
# those cascades, not `delete_image`, are how most objects are orphaned.
#
# `pre_delete`, not `post_delete`: the row (and its `storage_key`) must still be
# readable. Both run inside the deletion transaction, so a tombstone cannot
# survive a rolled-back delete, nor a delete outlive its tombstone.
#
# Keys are also recorded for rows deleted through
# `HANDLERS.images.delete_image`, which deletes the objects synchronously first.
# The duplicate work is a no-op (S3 `DeleteObject` on a missing key succeeds)
# and it buys a retry for the variant deletes that method swallows.


@receiver(pre_delete, sender=ProjectImage)
def record_orphaned_image_object(
    sender: Any, instance: ProjectImage, **kwargs: Any
) -> None:
    OrphanedStorageObject.objects.get_or_create(storage_key=instance.storage_key)


@receiver(pre_delete, sender=ImageVariant)
def record_orphaned_variant_object(
    sender: Any, instance: ImageVariant, **kwargs: Any
) -> None:
    OrphanedStorageObject.objects.get_or_create(storage_key=instance.storage_key)
