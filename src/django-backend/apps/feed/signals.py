"""Appends feed events from the things that happen elsewhere.

Signals rather than service-layer calls on purpose: competitions are decided in
Django admin, projects are approved there too, and articles publish through the
API. One hook per source catches all three paths, and it is also what lets the
backfill and the live path share a single appender.
"""

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.articles.models import Article, ArticleState
from apps.projects.models import Competition, Project, ProjectStatus
from services import HANDLERS


@receiver(post_save, sender=Article)
def append_on_article_publish(sender: Any, instance: Article, **kwargs: Any) -> None:
    if instance.state != ArticleState.PUBLISHED:
        return
    handler = HANDLERS.feed
    # Idempotent on the article, so an edit-after-publish adds nothing.
    handler.append_article_published(instance)
    # Supersede whatever the article is a write-up of. Also idempotent: the
    # target is only taken if it has not been superseded already.
    handler.link_article_to_event(instance, instance.about_feed_event_id)


@receiver(post_save, sender=Project)
def append_on_project_approval(sender: Any, instance: Project, **kwargs: Any) -> None:
    if instance.status != ProjectStatus.APPROVED:
        return
    HANDLERS.feed.append_project_published(instance)


@receiver(post_save, sender=Competition)
def append_on_competition_change(
    sender: Any, instance: Competition, **kwargs: Any
) -> None:
    handler = HANDLERS.feed
    handler.append_competition_opened(instance)
    handler.append_competition_submissions_closed(instance)
    if instance.winner_id is not None:
        handler.append_competition_winner(instance)
