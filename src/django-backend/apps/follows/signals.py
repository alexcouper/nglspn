from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.follows.models import Channel, Follow, FollowedChannel

# Postgres caps the parameters in a single statement; batching keeps the house
# project's follower count off that ceiling.
ENROL_BATCH_SIZE = 1000


@receiver(post_save, sender=Channel)
def enrol_followers_in_new_channel(
    sender: Any,
    instance: Channel,
    created: bool,  # noqa: FBT001
    **kwargs: Any,
) -> None:
    """Subscribe everyone already following the project to its new channel.

    Following a project is the consent; a follower who wants out unfollows the
    project, after which no future channel can reach them. Channels that
    predate a follow are still enrolled by `DjangoFollowHandler.follow` — this
    only covers the ones that arrive afterwards.

    The hook is the model, not `HANDLERS.articles.add_channel`, because the
    Django admin (`apps/follows/admin.py`) writes `Channel` directly and never
    reaches the service layer. `bulk_create` sends no `post_save`, so a
    bulk-created channel — and any data migration, which uses historical model
    classes — enrols nobody and has to write the rows itself.

    Renames must not enrol: a follower who unticked the channel would silently
    reappear on it the next time an admin fixed a typo.
    """
    if not created:
        return

    follows = Follow.objects.filter(project_id=instance.project_id).iterator()
    FollowedChannel.objects.bulk_create(
        [FollowedChannel(follow=follow, channel=instance) for follow in follows],
        batch_size=ENROL_BATCH_SIZE,
        # A `follow_channel` call racing the channel insert is the only way a
        # row for a channel this new can already exist.
        ignore_conflicts=True,
    )
