import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.projects.models import Project

# The one channel a person has. Created by `HANDLERS.articles.publish` the
# first time one of their author-owned articles goes out, never at signup, and
# never shown by name: the two surfaces that print a channel name hide it for
# an author-owned article.
PERSONAL_CHANNEL_NAME = "Articles"


class Channel(models.Model):
    """A stream of articles people can follow: a project's, or a person's.

    Exactly one of `project` and `owner` is set. A project has as many channels
    as its contributors make; a person has one, and nothing but publishing
    creates it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="channels",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personal_channels",
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "channels"
        constraints = [
            models.UniqueConstraint(
                fields=("project", "name"),
                condition=Q(project__isnull=False),
                name="channels_project_name_uniq",
            ),
            models.UniqueConstraint(
                fields=("owner", "name"),
                condition=Q(owner__isnull=False),
                name="channels_owner_name_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(project__isnull=False, owner__isnull=True)
                    | Q(project__isnull=True, owner__isnull=False)
                ),
                name="channels_exactly_one_owner",
            ),
        ]

    def __str__(self) -> str:
        holder = self.project.title if self.project_id else str(self.owner)
        return f"{holder}: {self.name}"


class Follow(models.Model):
    """`user` follows a project or a person. Exactly one target is set.

    Following a person reaches only their personal channel — never their
    projects, comments or competition entries. The channel rows under the
    follow (`FollowedChannel`) are what the fan-out reads; the target here is
    what the button toggles and the Following page lists.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follows",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="followers",
    )
    followed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="followed_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "follows"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "project"),
                condition=Q(project__isnull=False),
                name="follows_user_project_uniq",
            ),
            models.UniqueConstraint(
                fields=("user", "followed_user"),
                condition=Q(followed_user__isnull=False),
                name="follows_user_followed_user_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(project__isnull=False, followed_user__isnull=True)
                    | Q(project__isnull=True, followed_user__isnull=False)
                ),
                name="follows_exactly_one_target",
            ),
            models.CheckConstraint(
                condition=~Q(followed_user=F("user")),
                name="follows_not_self",
            ),
        ]

    def __str__(self) -> str:
        target = self.project if self.project_id else self.followed_user
        return f"{self.user} → {target}"


class FollowedChannel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follow = models.ForeignKey(
        Follow,
        on_delete=models.CASCADE,
        related_name="followed_channels",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
    )

    class Meta:
        # Table name pinned: the row identity is what carries "is followed";
        # renaming the table buys nothing and would invalidate any raw-SQL
        # references. Pre-existing rows survive the column drop unchanged.
        db_table = "follow_channel_preferences"
        unique_together = (("follow", "channel"),)

    def __str__(self) -> str:
        return f"{self.follow} / {self.channel.name}"
