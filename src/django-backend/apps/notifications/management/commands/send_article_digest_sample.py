"""Send every article digest layout to one address, for looking at in a mail client.

The admin preview renders the HTML in a browser, which is not where the email
is read. This builds each layout from the newest published articles through
the same `build_article_digest` the worker uses, and sends it with the
configured email backend. Nothing is logged to `SentEmail` and no Notification
row is touched, so it is safe to run against production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.articles.models import Article, ArticleState
from apps.notifications.models import Notification
from services.email.django_impl import render_email
from services.email.django_impl.article_digest import (
    LAYOUT_LEAD,
    LAYOUT_LIST,
    LAYOUT_SINGLE,
    LAYOUTS,
    LIST_LAYOUT_MIN_ARTICLES,
    build_article_digest,
    with_article_relations,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from collections.abc import Sequence

    from django.db.models import QuerySet

# How many of the newest articles each layout is handed. The list layout gets
# the number that would trigger it for real; the lead layout the most it can
# show before falling back to the list.
_ARTICLES_BY_LAYOUT = {
    LAYOUT_SINGLE: 1,
    LAYOUT_LEAD: LIST_LAYOUT_MIN_ARTICLES - 1,
    LAYOUT_LIST: LIST_LAYOUT_MIN_ARTICLES,
}


class Command(BaseCommand):
    help = "Send sample article digest emails, one per layout, to an address."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--to", required=True, help="Address to send to.")
        parser.add_argument(
            "--layout",
            choices=[*LAYOUTS, "all"],
            default="all",
            help="One layout, or all three (default).",
        )
        parser.add_argument(
            "--article",
            help="Slug or id of the article to lead with; default is the newest.",
        )

    def handle(self, *args, **options) -> None:
        to = options["to"]
        layouts = LAYOUTS if options["layout"] == "all" else (options["layout"],)
        articles = _newest_published(
            options["article"], max(_ARTICLES_BY_LAYOUT.values())
        )
        if not articles:
            msg = "No published articles to build a digest from."
            raise CommandError(msg)

        for layout in layouts:
            batch = articles[: _ARTICLES_BY_LAYOUT[layout]]
            digest = build_article_digest(_unsaved_notifications(batch), layout=layout)
            html, text = render_email(digest.template_name, digest.context)
            subject = f"[digest sample: {layout}] {digest.subject}"
            email = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to],
            )
            email.attach_alternative(html, "text/html")
            email.send(fail_silently=False)
            self.stdout.write(f"{layout}: sent {len(batch)} article(s) as {subject!r}")


def _newest_published(lead: str | None, limit: int) -> list[Article]:
    queryset = with_article_relations(
        Article.objects.filter(state=ArticleState.PUBLISHED).order_by("-published_at")
    )
    articles = list(queryset[:limit])
    if lead is None:
        return articles
    chosen = next((a for a in articles if lead in (a.slug, str(a.id))), None)
    if chosen is None:
        chosen = queryset.filter(slug=lead).first() or _by_id(queryset, lead)
    if chosen is None:
        msg = f"No published article with slug or id {lead!r}."
        raise CommandError(msg)
    return [chosen, *[a for a in articles if a.pk != chosen.pk]][:limit]


def _by_id(queryset: QuerySet[Article], value: str) -> Article | None:
    try:
        article_id = UUID(value)
    except ValueError:
        return None
    return queryset.filter(pk=article_id).first()


def _unsaved_notifications(articles: Sequence[Article]) -> list[Notification]:
    # Unsaved rows: the builder reads `article` and `created_at` and nothing
    # else, and nothing here should leave a Notification behind.
    now = timezone.now()
    return [Notification(article=article, created_at=now) for article in articles]
