from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.projects.models import Project, ProjectContributor

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
