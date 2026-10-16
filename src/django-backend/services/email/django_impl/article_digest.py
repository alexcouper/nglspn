"""Build the article digest email from a recipient's notifications.

One batch, three layouts, chosen by how many articles are in it. The sender
(`DjangoEmailHandler.send_article_digest_email`) and the admin preview
(`apps/notifications/admin.py`) both come through `build_article_digest`, so
they cannot disagree about what goes out.

- One article: subject `<Project>: <Title>`, or the title alone for the
  house project; template `article_digest_single`.
- Two to `LIST_LAYOUT_MIN_ARTICLES - 1`: subject names the newest and adds
  `, and N more`; template `article_digest_lead`.
- `LIST_LAYOUT_MIN_ARTICLES` or more: subject `N new articles - Naglasúpan`;
  template `article_digest`, today's list.

The single and lead subjects carry no ` - Naglasúpan` suffix: the sender name
has the brand, which is also why the house project's own name is left out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

from services.articles.render import excerpt_markdown, render_markdown_for_email
from services.articles.summary import derive_summary
from services.email import EMAIL_LOGO_URL
from services.images.django_impl.query import gallery_prefetch
from services.project.django_impl.query import variant_url

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import QuerySet

    from apps.articles.models import Article
    from apps.notifications.models import Notification

# Tuning constants. The admin digest preview (`?layout=` forces a template) is
# where to check them against real batches.
LIST_LAYOUT_MIN_ARTICLES = 5
LEAD_FULL_BODY_MAX_CHARS = 1200
LEAD_EXCERPT_MAX_CHARS = 800
ARTICLE_DIGEST_EXCERPT_MAX = 500

LAYOUT_SINGLE = "single"
LAYOUT_LEAD = "lead"
LAYOUT_LIST = "list"
LAYOUTS = (LAYOUT_SINGLE, LAYOUT_LEAD, LAYOUT_LIST)
_TEMPLATE_BY_LAYOUT = {
    LAYOUT_SINGLE: "article_digest_single",
    LAYOUT_LEAD: "article_digest_lead",
    LAYOUT_LIST: "article_digest",
}


@dataclass(frozen=True)
class ArticleDigestEmail:
    subject: str
    layout: str
    template_name: str
    context: dict


def _relations(prefix: str) -> tuple[list[str], list]:
    """Everything the builder reads off an article, as select/prefetch lookups.

    `prefix` walks the lookups across a relation: `"article__"` from a
    Notification queryset, `""` from an Article queryset.
    """
    select = [
        f"{prefix}project",
        f"{prefix}channel",
        f"{prefix}author",
        f"{prefix}listing_image",
    ]
    prefetch = [
        f"{prefix}listing_image__variants",
        # Body images, for the medium-variant substitution.
        f"{prefix}images__variants",
        # `get_project_icon_url` falls back to `images[0]` with no filtering of
        # its own, so the prefetch is the only thing keeping an article figure
        # or a failed upload out of the project icon.
        gallery_prefetch(f"{prefix}project__images"),
    ]
    return select, prefetch


def with_article_digest_relations(
    queryset: QuerySet[Notification],
) -> QuerySet[Notification]:
    """A Notification queryset with everything the builder reads fetched up front.

    Shared by the digest worker and the admin preview so neither can miss a
    relation and pay for it once per article.
    """
    select, prefetch = _relations("article__")
    return queryset.select_related("recipient", "article", *select).prefetch_related(
        *prefetch
    )


def with_article_relations(queryset: QuerySet[Article]) -> QuerySet[Article]:
    """The same, for callers that start from articles rather than notifications."""
    select, prefetch = _relations("")
    return queryset.select_related(*select).prefetch_related(*prefetch)


def build_article_digest(
    notifications: Sequence[Notification], *, layout: str | None = None
) -> ArticleDigestEmail:
    """Subject, template and context for one recipient's batch.

    `layout` forces a template regardless of batch size; the admin preview uses
    it to look at the lead and list layouts without manufacturing a batch.
    """
    ordered = _newest_first(notifications)
    if layout is None:
        layout = _layout_for(len(ordered))
    context = {
        "site_url": settings.FRONTEND_URL,
        "profile_url": f"{settings.FRONTEND_URL}/profile",
        "logo_url": EMAIL_LOGO_URL,
        "current_year": timezone.now().year,
    }
    lead = ordered[0].article

    if layout == LAYOUT_SINGLE:
        subject = _subject_title(lead)
        context["article"] = _full_article_context(lead)
    elif layout == LAYOUT_LEAD:
        rest = len(ordered) - 1
        subject = f"{_subject_title(lead)}, and {rest} more"
        context["lead"] = _lead_article_context(lead)
        context["entries"] = build_article_digest_entries(ordered[1:])
    else:
        subject = f"{len(ordered)} new articles - Naglasúpan"
        context["entries"] = build_article_digest_entries(ordered)

    return ArticleDigestEmail(
        subject=subject,
        layout=layout,
        template_name=_TEMPLATE_BY_LAYOUT[layout],
        context=context,
    )


def _layout_for(count: int) -> str:
    if count == 1:
        return LAYOUT_SINGLE
    if count < LIST_LAYOUT_MIN_ARTICLES:
        return LAYOUT_LEAD
    return LAYOUT_LIST


def _newest_first(notifications: Sequence[Notification]) -> list[Notification]:
    # Same key as the bell's `_build_article_group`.
    return sorted(
        notifications,
        key=lambda n: n.article.published_at or n.created_at,
        reverse=True,
    )


def _subject_title(article: Article) -> str:
    if article.project.is_house_project:
        return article.title
    return f"{article.project.title}: {article.title}"


def _project_url(article: Article) -> str:
    return (
        f"{settings.FRONTEND_URL}/projects/{article.project.slug or article.project.id}"
    )


def _article_url(article: Article) -> str:
    return f"{_project_url(article)}/articles/{article.slug or article.id}"


def _author_name(article: Article) -> str:
    author = article.author
    if author is None or author.is_system_user:
        return ""
    return author.full_name or ""


def _body_image_urls(article: Article) -> dict[str, str]:
    """Original URL to medium-variant URL for every image on the article."""
    return {image.url: variant_url(image, "medium") for image in article.images.all()}


def _byline_context(article: Article) -> dict:
    return {
        "article_title": article.title,
        "article_url": _article_url(article),
        "project_title": article.project.title,
        "project_url": _project_url(article),
        "channel_name": article.channel.name,
        "published_at": article.published_at,
        "author_name": _author_name(article),
    }


def _full_article_context(article: Article) -> dict:
    return {
        **_byline_context(article),
        "body_html": render_markdown_for_email(
            article.body, image_urls=_body_image_urls(article)
        ),
        "body_markdown": article.body,
    }


def _lead_article_context(article: Article) -> dict:
    excerpt, truncated = excerpt_markdown(
        article.body,
        full_max=LEAD_FULL_BODY_MAX_CHARS,
        excerpt_max=LEAD_EXCERPT_MAX_CHARS,
    )
    return {
        **_byline_context(article),
        "body_html": render_markdown_for_email(
            excerpt, image_urls=_body_image_urls(article)
        ),
        "body_markdown": excerpt,
        "truncated": truncated,
    }


def _digest_article_image_url(article: Article) -> str | None:
    from services import REPO

    hero = article.listing_image
    if hero is not None:
        return variant_url(hero, "thumb")
    return REPO.project.get_project_icon_url(article.project)


def build_article_digest_entries(notifications: Sequence[Notification]) -> list[dict]:
    """The title-plus-excerpt entries the lead and list layouts share."""
    entries = []
    for n in notifications:
        article = n.article
        # Same excerpt the listing card shows: the entry is plain text, so the
        # markdown body has to be flattened rather than pasted in raw.
        body_excerpt = article.summary or derive_summary(
            article.body or "", limit=ARTICLE_DIGEST_EXCERPT_MAX
        )
        entries.append(
            {
                "project_title": article.project.title,
                "project_url": _project_url(article),
                "channel_name": article.channel.name,
                "article_title": article.title,
                "article_image_url": _digest_article_image_url(article),
                "body_excerpt": body_excerpt,
                "article_url": _article_url(article),
            }
        )
    return entries
