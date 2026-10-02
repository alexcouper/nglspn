"""Appends feed events from the things that happen elsewhere.

Signals rather than service-layer calls on purpose: projects are approved in
Django admin and articles publish through the API. One hook per source catches
both paths, and it is also what lets the backfill and the live path share a
single appender.
"""

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.articles.models import Article, ArticleState
from apps.projects.models import Project, ProjectStatus
from services import HANDLERS


@receiver(post_save, sender=Article)
def append_on_article_publish(sender: Any, instance: Article, **kwargs: Any) -> None:
    if instance.state != ArticleState.PUBLISHED:
        return
    # Idempotent on the article, so an edit-after-publish adds nothing.
    HANDLERS.feed.append_article_published(instance)


@receiver(post_save, sender=Project)
def append_on_project_approval(sender: Any, instance: Project, **kwargs: Any) -> None:
    if instance.status != ProjectStatus.APPROVED:
        return
    HANDLERS.feed.append_project_published(instance)
