"""Collapse the house project's "Product Updates" channel into "Updates".

Both channels did one job with different subscriber lists. `Updates` exists on
the house project only because every Project gets a default channel from the
`post_save` signal; `Product Updates` was seeded by 0002 from the legacy
`email_opt_in_platform_updates` flag. 0002 seeded `Updates` with
`email_enabled=True` unconditionally, so users who had opted out of
platform-update email still received anything published there.

The merge keeps the `Product Updates` subscriber list, which is the one
carrying real intent. Rather than deleting `FollowedChannel` rows off
`Updates` — destroying the list being kept — it moves the articles across,
deletes `Updates`, and renames `Product Updates` into its place.

Order is forced twice over: `Article.channel` is `on_delete=PROTECT`, so the
reassignment must precede the delete; `Channel.unique_together (project, name)`
means the rename must follow it.
"""

import logging

from django.db import migrations, transaction

logger = logging.getLogger(__name__)

UPDATES_CHANNEL = "Updates"
PRODUCT_UPDATES_CHANNEL = "Product Updates"


def merge_product_updates_into_updates(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Channel = apps.get_model("follows", "Channel")
    Article = apps.get_model("articles", "Article")

    house = Project.objects.filter(is_house_project=True).first()
    if house is None:
        logger.warning(
            "merge_product_updates_into_updates: no house project; skipping "
            "(dev/test DB case)"
        )
        return

    product_updates = Channel.objects.filter(
        project=house, name=PRODUCT_UPDATES_CHANNEL
    ).first()
    if product_updates is None:
        # Already merged, or a fresh install that never had the channel.
        return

    with transaction.atomic():
        updates = Channel.objects.filter(project=house, name=UPDATES_CHANNEL).first()
        if updates is not None:
            # PROTECT on Article.channel: move articles before deleting.
            Article.objects.filter(channel=updates).update(channel=product_updates)
            # Cascades this channel's FollowedChannel rows away.
            updates.delete()

        product_updates.name = UPDATES_CHANNEL
        product_updates.save(update_fields=["name"])


def reverse_noop(apps, schema_editor):
    """Merge is destructive — reverse is documented as a no-op.

    The `FollowedChannel` rows cascaded away with the old `Updates` channel
    cannot be reconstructed, and the two article sets are indistinguishable
    once merged. Recovery is forward-only: re-enrol users through the follow
    popover, or `apps.follows.services.anoint_house_project`. Documented here
    so a future reverse plan does not assume this step undid itself. Same
    stance as 0004_sweep_both_off_rows.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("follows", "0005_drop_legacy_booleans"),
        ("articles", "0005_alter_article_listing_image"),
    ]

    operations = [
        migrations.RunPython(
            merge_product_updates_into_updates, reverse_code=reverse_noop
        ),
    ]
