from __future__ import annotations

import uuid

import pytest

from apps.articles.models import Article
from apps.follows.models import Channel, Follow, FollowedChannel
from services.articles.django_impl.handler import DjangoArticleHandler
from services.articles.exceptions import (
    ChannelHasArticlesError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    DuplicateChannelNameError,
    LastChannelError,
)
from tests.factories import (
    ChannelFactory,
    ProjectFactory,
    PublishedArticleFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestAddChannel:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_creates_channel(self):
        project = ProjectFactory()

        channel = self.handler.add_channel(project.id, "Releases")

        assert channel.pk is not None
        assert channel.name == "Releases"
        assert channel.project_id == project.id

    def test_duplicate_name_raises(self):
        project = ProjectFactory()
        ChannelFactory(project=project, name="Releases")

        with pytest.raises(DuplicateChannelNameError):
            self.handler.add_channel(project.id, "Releases")

    def test_same_name_on_different_project_allowed(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        self.handler.add_channel(project_a.id, "Releases")

        # No exception.
        self.handler.add_channel(project_b.id, "Releases")


@pytest.mark.django_db
class TestRenameChannel:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_renames_in_place(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Releases")

        result = self.handler.rename_channel(channel.id, "Launches")

        assert result.id == channel.id
        assert result.name == "Launches"

    def test_preserves_follower_row(self):
        """Rename keeps the row's FK intact — channel name is not on the row."""
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Releases")
        user = UserFactory()
        follow = Follow.objects.create(user=user, project=project)
        fc = FollowedChannel.objects.create(follow=follow, channel=channel)

        self.handler.rename_channel(channel.id, "Launches")

        fc.refresh_from_db()
        assert fc.channel_id == channel.id

    def test_rename_to_duplicate_name_raises(self):
        project = ProjectFactory()
        ChannelFactory(project=project, name="Releases")
        target = ChannelFactory(project=project, name="Launches")

        with pytest.raises(DuplicateChannelNameError):
            self.handler.rename_channel(target.id, "Releases")

    def test_no_op_when_name_unchanged(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Releases")

        result = self.handler.rename_channel(channel.id, "Releases")

        assert result.name == "Releases"

    def test_unknown_channel_raises(self):
        with pytest.raises(ChannelNotFoundError):
            self.handler.rename_channel(uuid.uuid4(), "x")


@pytest.mark.django_db
class TestDeleteChannel:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_deletes_empty_non_only_channel(self):
        project = ProjectFactory()
        # Project signal seeded "Updates"; add a second so we can delete one.
        second = ChannelFactory(project=project, name="Releases")

        self.handler.delete_channel(second.id)

        assert not Channel.objects.filter(pk=second.id).exists()

    def test_rejects_delete_with_articles(self):
        project = ProjectFactory()
        target = ChannelFactory(project=project, name="Releases")
        PublishedArticleFactory(project=project, channel=target)

        with pytest.raises(ChannelHasArticlesError) as excinfo:
            self.handler.delete_channel(target.id)

        assert excinfo.value.article_count == 1
        assert Channel.objects.filter(pk=target.id).exists()

    def test_rejects_delete_of_only_channel(self):
        project = ProjectFactory()
        only = Channel.objects.get(project=project, name="Updates")

        with pytest.raises(LastChannelError):
            self.handler.delete_channel(only.id)

        assert Channel.objects.filter(pk=only.id).exists()

    def test_cascade_deletes_preferences(self):
        project = ProjectFactory()
        second = ChannelFactory(project=project, name="Releases")
        user = UserFactory()
        follow = Follow.objects.create(user=user, project=project)
        FollowedChannel.objects.create(follow=follow, channel=second)

        self.handler.delete_channel(second.id)

        assert not FollowedChannel.objects.filter(channel=second).exists()

    def test_unknown_channel_raises(self):
        with pytest.raises(ChannelNotFoundError):
            self.handler.delete_channel(uuid.uuid4())


@pytest.mark.django_db
class TestBulkReassign:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_moves_articles_to_target_channel(self):
        project = ProjectFactory()
        source = ChannelFactory(project=project, name="Releases")
        target = ChannelFactory(project=project, name="News")
        a1 = PublishedArticleFactory(project=project, channel=source)
        a2 = PublishedArticleFactory(project=project, channel=source)

        moved = self.handler.bulk_reassign_articles(source.id, target.id)

        assert moved == 2
        a1.refresh_from_db()
        a2.refresh_from_db()
        assert a1.channel_id == target.id
        assert a2.channel_id == target.id
        assert not Article.objects.filter(channel=source).exists()

    def test_cross_project_reassign_rejected(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        source = ChannelFactory(project=project_a, name="Releases")
        target = ChannelFactory(project=project_b, name="Releases")

        with pytest.raises(ChannelOnWrongProjectError):
            self.handler.bulk_reassign_articles(source.id, target.id)

    def test_unknown_channel_raises(self):
        project = ProjectFactory()
        target = ChannelFactory(project=project, name="Releases")
        with pytest.raises(ChannelNotFoundError):
            self.handler.bulk_reassign_articles(uuid.uuid4(), target.id)
