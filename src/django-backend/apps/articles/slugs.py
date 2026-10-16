from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils.text import slugify

from apps.articles.models import Article
from apps.projects.models import transliterate_icelandic

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

MAX_COLLISION_ATTEMPTS = 1000

# Article.slug is max_length=200; reserve room for the largest possible
# "-{n}" suffix appended during collision resolution.
_SLUG_MAX_LENGTH = 200
_MAX_BASE_LENGTH = _SLUG_MAX_LENGTH - len(f"-{MAX_COLLISION_ATTEMPTS}")

_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")


def _truncate_base(base: str) -> str:
    if len(base) <= _MAX_BASE_LENGTH:
        return base
    return base[:_MAX_BASE_LENGTH].rstrip("-")


def _candidate(base: str, n: int) -> str:
    return base if n == 1 else f"{base}-{n}"


def _slugify_article_title(text: str) -> str:
    text = transliterate_icelandic(text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return slugify(text)


def _slug_siblings(article: Article) -> QuerySet[Article]:
    """The articles a slug must be unique among: the same project's, or for an
    author-owned article the same author's other author-owned ones.

    Mirrors the two partial unique constraints on `Article`, so the pre-check
    and the constraint the retry loop falls back on agree.
    """
    if article.project_id is not None:
        return Article.objects.filter(project_id=article.project_id)
    return Article.objects.filter(author_id=article.author_id, project__isnull=True)


def assign_unique_article_slug(article: Article) -> None:
    """Generate and persist a unique slug for an article being published.

    Uniqueness is scoped to the article's container (see `_slug_siblings`),
    not global — two projects, or two authors, can independently publish
    articles with the same slug. Race-safe: retries on DB-level
    unique-constraint violations.
    """
    base = _truncate_base(_slugify_article_title(article.title) or "article")
    existing = _slug_siblings(article)
    if article.pk is not None:
        existing = existing.exclude(pk=article.pk)
    n = 1
    for _ in range(MAX_COLLISION_ATTEMPTS):
        while existing.filter(slug=_candidate(base, n)).exists():
            n += 1
        candidate = _candidate(base, n)
        try:
            with transaction.atomic():
                article.slug = candidate
                article.save(update_fields=["slug"])
        except IntegrityError:
            n += 1
            continue
        else:
            return
    msg = f"Could not allocate a unique slug for article {article.pk}"
    raise RuntimeError(msg)


def project_has_article_with_slug(project_id: UUID, slug: str) -> bool:
    return Article.objects.filter(project_id=project_id, slug=slug).exists()


def author_has_article_with_slug(author_id: UUID, slug: str) -> bool:
    return Article.objects.filter(
        author_id=author_id, project__isnull=True, slug=slug
    ).exists()
