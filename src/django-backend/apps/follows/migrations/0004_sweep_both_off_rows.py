import logging

from django.db import migrations

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


def sweep_both_off(apps, schema_editor):
    """Delete FollowedChannel rows whose legacy switches are both False.

    Both-off was the "I follow this project but want neither email nor in-app
    on this channel" cohort — that's no longer expressible. Drop those rows
    before the booleans are removed in 0005 so the row identity no longer
    represents a silenced follow. Leaves Follow rows untouched.
    """
    FollowedChannel = apps.get_model("follows", "FollowedChannel")
    qs = FollowedChannel.objects.filter(email_enabled=False, in_app_enabled=False)
    kept_before = FollowedChannel.objects.count() - qs.count()

    deleted_total = 0
    while True:
        batch_ids = list(qs.values_list("pk", flat=True)[:_BATCH_SIZE])
        if not batch_ids:
            break
        deleted, _ = FollowedChannel.objects.filter(pk__in=batch_ids).delete()
        deleted_total += deleted

    logger.info(
        "follows.sweep_both_off: rows_kept=%d rows_deleted=%d",
        kept_before,
        deleted_total,
    )


def reverse_noop(apps, schema_editor):
    """Sweep is destructive — reverse is documented as a no-op.

    Rollback after the column drop requires forward fix anyway; documenting
    that here so a future reverse plan doesn't assume this step undid itself.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("follows", "0003_rename_follow_channel_preference"),
    ]

    operations = [
        migrations.RunPython(sweep_both_off, reverse_code=reverse_noop),
    ]
