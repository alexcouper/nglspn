from django.db import IntegrityError, transaction
from django.utils.text import slugify

from apps.projects.models import Project, transliterate_icelandic

MAX_COLLISION_ATTEMPTS = 1000


def _candidate(base: str, n: int) -> str:
    return base if n == 1 else f"{base}-{n}"


def generate_unique_project_slug(title: str) -> str:
    base = slugify(transliterate_icelandic(title)) or "project"
    n = 1
    while Project.objects.filter(slug=_candidate(base, n)).exists():
        n += 1
    return _candidate(base, n)


def assign_unique_slug(project: Project) -> None:
    """Generate and persist a unique slug for an unpublished project.

    Race-safe: retries on DB-level unique-constraint violations raised by
    concurrent publishes choosing the same suffix.
    """
    base = slugify(transliterate_icelandic(project.title)) or "project"
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
