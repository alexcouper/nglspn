from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.projects.models import Project, ProjectContributor


@receiver(post_save, sender=ProjectContributor)
def recompute_on_contributor_save(
    sender: Any, instance: ProjectContributor, **kwargs: Any
) -> None:
    instance.project.recompute_community_tipoff()


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
