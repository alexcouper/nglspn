from django.db import migrations, models

# Duplicated rather than imported from apps.articles.models: a migration has to
# keep running against the vocabulary it shipped with, and a fifth visibility
# state added later must not retroactively change what this backfilled.
GLOBALLY_VISIBLE_STATES = ("auto", "approved")


def backfill_approved_at(apps, schema_editor):  # noqa: ARG001
    """Seed the approval time for articles that were visible before the field.

    Nothing recorded when an article became visible, so the only honest proxy is
    when it published. That is exact for the trusted-author case — publishing is
    the approval — and early for one that waited in a review queue, which is the
    harmless direction: the field decides whether an article is fresh enough to
    notify anyone about, and no existing row is owed a notification.
    """
    Article = apps.get_model("articles", "Article")

    Article.objects.filter(
        state="published",
        global_visibility__in=GLOBALLY_VISIBLE_STATES,
        approved_at__isnull=True,
        published_at__isnull=False,
    ).update(approved_at=models.F("published_at"))


def noop(apps, schema_editor):  # noqa: ARG001
    # Reversing leaves the values in place; the field drop removes them.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0007_article_approved_at"),
    ]

    operations = [
        migrations.RunPython(backfill_approved_at, noop),
    ]
