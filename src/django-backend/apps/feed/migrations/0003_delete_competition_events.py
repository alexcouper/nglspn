"""Delete the competition milestone entries before their column goes.

Competition opened / submissions closed / winner announced no longer appear in
the feed. Their rows have no other subject, so they would fail the
`feed_events_has_subject` check the moment `competition` is dropped.

A migration of its own rather than a step in 0004: Postgres refuses to ALTER a
table that still has trigger events pending from a DELETE in the same
transaction.
"""

from django.db import migrations


def delete_competition_events(apps, schema_editor):
    FeedEvent = apps.get_model("feed", "FeedEvent")
    FeedEvent.objects.filter(competition__isnull=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("feed", "0002_remove_superseding"),
    ]

    operations = [
        # Nothing to restore on the way back: the appenders that wrote these
        # rows are gone with them.
        migrations.RunPython(delete_competition_events, migrations.RunPython.noop),
    ]
