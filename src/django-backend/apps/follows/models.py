import uuid

from django.conf import settings
from django.db import models

from apps.projects.models import Project


class Channel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="channels",
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "channels"
        unique_together = (("project", "name"),)

    def __str__(self) -> str:
        return f"{self.project.title}: {self.name}"


class Follow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follows",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "follows"
        unique_together = (("user", "project"),)

    def __str__(self) -> str:
        return f"{self.user} → {self.project}"


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
