import re

from django.db import IntegrityError, transaction
from django.utils.text import slugify

from apps.projects.models import Project, transliterate_icelandic

MAX_COLLISION_ATTEMPTS = 1000

_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")


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
    base = _slugify_preserving_separators(title) or "project"
    n = 1
    while Project.objects.filter(slug=_candidate(base, n)).exists():
        n += 1
    return _candidate(base, n)


def assign_unique_slug(project: Project) -> None:
    """Generate and persist a unique slug for an unpublished project.

    Race-safe: retries on DB-level unique-constraint violations raised by
    concurrent publishes choosing the same suffix.
    """
    base = _slugify_preserving_separators(project.title) or "project"
    n = 1
    for _ in range(MAX_COLLISION_ATTEMPTS):
        while Project.objects.filter(slug=_candidate(base, n)).exists():
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
