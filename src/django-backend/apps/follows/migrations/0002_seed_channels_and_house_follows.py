"""Seed channels and back-fill follows for existing users.

This migration:

- Flags the Naglasúpan Project row (by slug) with ``is_house_project = True``.
- Seeds the three named channels on Naglasúpan
  (``Updates``, ``Competition Winners``, ``Product Updates``).
- Seeds the ``Updates`` channel on every other existing Project.
- For every active non-system User, creates a Follow on Naglasúpan with
  ``FollowChannelPreference`` rows seeded from the legacy
  ``email_opt_in_*`` flags.

If the Naglasúpan row does not exist (greenfield dev/test DB), the migration
no-ops cleanly with a warning.
"""

import logging

from django.db import migrations, transaction

logger = logging.getLogger(__name__)

HOUSE_PROJECT_SLUG = "naglasupan"
UPDATES_CHANNEL = "Updates"
COMPETITION_WINNERS_CHANNEL = "Competition Winners"
PRODUCT_UPDATES_CHANNEL = "Product Updates"
BATCH_SIZE = 1000


def seed_channels_and_house_follows(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    User = apps.get_model("users", "User")
    Channel = apps.get_model("follows", "Channel")
    Follow = apps.get_model("follows", "Follow")
    FollowChannelPreference = apps.get_model("follows", "FollowChannelPreference")

    naglasupan = Project.objects.filter(slug=HOUSE_PROJECT_SLUG).first()
    if naglasupan is None:
        logger.warning(
            "seed_channels_and_house_follows: no Project with slug=%r found; "
            "skipping (dev/test DB case)",
            HOUSE_PROJECT_SLUG,
        )
        return

    with transaction.atomic():
        if not naglasupan.is_house_project:
            naglasupan.is_house_project = True
            naglasupan.save(update_fields=["is_house_project"])

        # Seed channels for Naglasúpan (signal won't fire here — frozen apps).
        updates, _ = Channel.objects.get_or_create(
            project=naglasupan, name=UPDATES_CHANNEL
        )
        competition_winners, _ = Channel.objects.get_or_create(
            project=naglasupan, name=COMPETITION_WINNERS_CHANNEL
        )
        product_updates, _ = Channel.objects.get_or_create(
            project=naglasupan, name=PRODUCT_UPDATES_CHANNEL
        )

        # Seed the default Updates channel on every other Project.
        for project in Project.objects.exclude(pk=naglasupan.pk).iterator(
            chunk_size=BATCH_SIZE
        ):
            Channel.objects.get_or_create(project=project, name=UPDATES_CHANNEL)

        # Backfill Follow + FollowChannelPreference rows for each eligible user.
        eligible_users = User.objects.filter(is_active=True, is_system_user=False)
        for user in eligible_users.iterator(chunk_size=BATCH_SIZE):
            follow, _ = Follow.objects.get_or_create(user=user, project=naglasupan)
            FollowChannelPreference.objects.update_or_create(
                follow=follow,
                channel=competition_winners,
                defaults={
                    "email_enabled": user.email_opt_in_competition_results,
                    "in_app_enabled": True,
                },
            )
            FollowChannelPreference.objects.update_or_create(
                follow=follow,
                channel=product_updates,
                defaults={
                    "email_enabled": user.email_opt_in_platform_updates,
                    "in_app_enabled": True,
                },
            )
            FollowChannelPreference.objects.update_or_create(
                follow=follow,
                channel=updates,
                defaults={"email_enabled": True, "in_app_enabled": True},
            )


def reverse_seed(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Channel = apps.get_model("follows", "Channel")
    Follow = apps.get_model("follows", "Follow")

    naglasupan = Project.objects.filter(slug=HOUSE_PROJECT_SLUG).first()
    if naglasupan is None:
        return

    with transaction.atomic():
        # Cascade-deletes preferences via the Follow FK.
        Follow.objects.filter(project=naglasupan).delete()
        Channel.objects.filter(
            project=naglasupan,
            name__in=[
                UPDATES_CHANNEL,
                COMPETITION_WINNERS_CHANNEL,
                PRODUCT_UPDATES_CHANNEL,
            ],
        ).delete()
        Channel.objects.filter(name=UPDATES_CHANNEL).delete()
        if naglasupan.is_house_project:
            naglasupan.is_house_project = False
            naglasupan.save(update_fields=["is_house_project"])


class Migration(migrations.Migration):
    dependencies = [
        ("follows", "0001_initial"),
        ("projects", "0043_project_is_house_project_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_channels_and_house_follows, reverse_code=reverse_seed
        ),
    ]
