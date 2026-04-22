import re

from django.db import migrations
from django.utils.text import slugify

_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")

# Self-contained copy of the transliteration mapping so this migration does
# not depend on live model-layer code that may change in future.
_ICELANDIC_TRANSLITERATION = {
    "á": "a",
    "ð": "d",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "ý": "y",
    "þ": "th",
    "æ": "ae",
    "ö": "o",
    "Á": "A",
    "Ð": "D",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "Ý": "Y",
    "Þ": "Th",
    "Æ": "Ae",
    "Ö": "O",
}


def _transliterate(text: str) -> str:
    for icelandic, ascii_equiv in _ICELANDIC_TRANSLITERATION.items():
        text = text.replace(icelandic, ascii_equiv)
    return text


def _slug_base(title: str) -> str:
    # Kept in sync with apps.projects.slugs._slugify_preserving_separators —
    # duplicated here so this migration stays self-contained.
    title = _transliterate(title)
    title = _NON_ALNUM_RE.sub(" ", title)
    return slugify(title)


def backfill(apps, schema_editor):
    Project = apps.get_model("projects", "Project")

    used_slugs = set(
        Project.objects.exclude(slug__isnull=True).values_list("slug", flat=True)
    )

    projects = Project.objects.exclude(status="draft").order_by("created_at")

    for project in projects:
        if project.slug is None:
            base = _slug_base(project.title) or "project"
            candidate = base
            n = 1
            while candidate in used_slugs:
                n += 1
                candidate = f"{base}-{n}"
            project.slug = candidate
            used_slugs.add(candidate)

        if project.published_at is None:
            project.published_at = project.approved_at or project.created_at

        project.save(update_fields=["slug", "published_at"])


def reverse(apps, schema_editor):
    # Non-destructive reverse: drop the values we set so the forward migration
    # can run again cleanly. Status is untouched.
    Project = apps.get_model("projects", "Project")
    Project.objects.exclude(status="draft").update(slug=None, published_at=None)


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0036_project_published_at_project_slug_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse),
    ]
