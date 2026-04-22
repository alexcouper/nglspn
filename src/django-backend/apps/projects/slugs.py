import re

from django.db import IntegrityError, transaction
from django.utils.text import slugify

from apps.projects.models import Project, transliterate_icelandic

MAX_COLLISION_ATTEMPTS = 1000

# Project.slug is max_length=110; reserve room for the largest possible
# "-{n}" suffix we might append during collision resolution.
_SLUG_MAX_LENGTH = 110
_MAX_BASE_LENGTH = _SLUG_MAX_LENGTH - len(f"-{MAX_COLLISION_ATTEMPTS}")

_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")


def _truncate_base(base: str) -> str:
    if len(base) <= _MAX_BASE_LENGTH:
        return base
    return base[:_MAX_BASE_LENGTH].rstrip("-")


def _candidate(base: str, n: int) -> str:
    return base if n == 1 else f"{base}-{n}"


def _slugify_preserving_separators(text: str) -> str:
    # Every non-alphanumeric run becomes a single separator, so URL-ish titles
    # like "foo.com/hello?x=1" slug to "foo-com-hello-x-1" instead of silently
    # dropping the punctuation and collapsing the words together.
    text = transliterate_icelandic(text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return slugify(text)


def generate_unique_project_slug(title: str) -> str:
    base = _truncate_base(_slugify_preserving_separators(title) or "project")
    n = 1
    while Project.objects.filter(slug=_candidate(base, n)).exists():
        n += 1
    return _candidate(base, n)


def assign_unique_slug(project: Project) -> None:
    """Generate and persist a unique slug for an unpublished project.

    Race-safe: retries on DB-level unique-constraint violations raised by
    concurrent publishes choosing the same suffix. Safe to re-run when the
    project already owns a slug — its own row is excluded from collision
    checks.
    """
    base = _truncate_base(_slugify_preserving_separators(project.title) or "project")
    existing = Project.objects.all()
    if project.pk is not None:
        existing = existing.exclude(pk=project.pk)
    n = 1
    for _ in range(MAX_COLLISION_ATTEMPTS):
        while existing.filter(slug=_candidate(base, n)).exists():
            n += 1
        candidate = _candidate(base, n)
        try:
            with transaction.atomic():
                project.slug = candidate
                project.save(update_fields=["slug"])
        except IntegrityError:
            n += 1
            continue
        else:
            return
    msg = f"Could not allocate a unique slug for title {project.title!r}"
    raise RuntimeError(msg)
