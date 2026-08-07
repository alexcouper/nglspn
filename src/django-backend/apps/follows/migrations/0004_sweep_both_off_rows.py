import logging

from django.db import migrations

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


def sweep_email_disabled(apps, schema_editor):
    """Delete FollowedChannel rows whose legacy `email_enabled` switch is off.

    After 0005 drops the booleans, the row *is* the subscription: following a
    channel means its articles reach you, at the cadence on your user record.
    So the only pre-change signal that survives the collapse is
    `email_enabled` — a row with it off has to go, or the user is resubscribed
    to mail they turned off.

    `in_app_enabled` is deliberately ignored. For every row seeded by
    0002_seed_channels_and_house_follows it is a constant `True` written by
    that migration, not a choice: the two legacy checkboxes those rows came
    from (`email_opt_in_competition_results`, `email_opt_in_platform_updates`)
    predate the in-app bell entirely. Keying on `email_enabled OR
    in_app_enabled` would therefore match every legacy row regardless of the
    opt-out and delete none of them.

    Rows where the user asked for in-app but not email are lost to the
    collapse — that state is not expressible once the booleans are gone, and
    erring toward a quiet inbox is the safer direction. Leaves Follow rows
    untouched: a Follow with no channels is a valid "following, no channels"
    state (see design decision 6).
    """
    FollowedChannel = apps.get_model("follows", "FollowedChannel")
    qs = FollowedChannel.objects.filter(email_enabled=False)
    kept_before = FollowedChannel.objects.count() - qs.count()

    deleted_total = 0
    while True:
        batch_ids = list(qs.values_list("pk", flat=True)[:_BATCH_SIZE])
        if not batch_ids:
            break
        deleted, _ = FollowedChannel.objects.filter(pk__in=batch_ids).delete()
        deleted_total += deleted

    logger.info(
        "follows.sweep_email_disabled: rows_kept=%d rows_deleted=%d",
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
        migrations.RunPython(sweep_email_disabled, reverse_code=reverse_noop),
    ]
