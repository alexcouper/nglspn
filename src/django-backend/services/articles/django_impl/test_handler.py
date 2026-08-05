from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.articles.models import (
    Article,
    ArticleGlobalVisibility,
    ArticleSource,
    ArticleState,
)
from apps.follows.models import Follow, FollowedChannel
from apps.notifications.models import Notification
from apps.users.models import ArticleEmailFrequency
from services.articles.django_impl.handler import DjangoArticleHandler
from services.articles.exceptions import (
    ArticleNotFoundError,
    ArticleNotPublishableError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    HeroImageOnWrongProjectError,
    PublishedArticleNeedsHeroImageError,
)
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestCreateDraft:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_creates_draft_with_minimal_fields(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project)

        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
        )

        assert article.pk is not None
        assert article.state == ArticleState.DRAFT
        assert article.source == ArticleSource.INTERNAL
        assert article.title == ""
        assert article.body == ""
        assert article.hero_image_id is None
        assert article.slug is None
        assert article.published_at is None
        assert article.global_visibility == ArticleGlobalVisibility.AUTO

    def test_rejects_channel_on_different_project(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        channel_b = ChannelFactory(project=project_b)

        with pytest.raises(ChannelOnWrongProjectError):
            self.handler.create_draft(
                project_id=project_a.id,
                channel_id=channel_b.id,
                author_id=project_a.creator.id,
            )

    def test_rejects_hero_image_on_different_project(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        channel = ChannelFactory(project=project_a)
        image_b = ProjectImageFactory(project=project_b)

        with pytest.raises(HeroImageOnWrongProjectError):
            self.handler.create_draft(
                project_id=project_a.id,
                channel_id=channel.id,
                author_id=project_a.creator.id,
                hero_image_id=image_b.id,
            )

    def test_unknown_channel_raises_channel_not_found(self):
        project = ProjectFactory()

        with pytest.raises(ChannelNotFoundError):
            self.handler.create_draft(
                project_id=project.id,
                channel_id=uuid.uuid4(),
                author_id=project.creator.id,
            )


@pytest.mark.django_db
class TestUpdateArticle:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_updates_only_passed_fields(self):
        article = ArticleFactory()
        old_body = article.body

        updated = self.handler.update_article(article.id, title="Brand new title")

        assert updated.title == "Brand new title"
        assert updated.body == old_body

    def test_channel_reassignment_validates_project(self):
        project = ProjectFactory()
        other_project = ProjectFactory()
        article = ArticleFactory(project=project)
        foreign_channel = ChannelFactory(project=other_project)

        with pytest.raises(ChannelOnWrongProjectError):
            self.handler.update_article(article.id, channel_id=foreign_channel.id)

    def test_editing_published_at_does_not_fire_notifications(self):
        """published_at edits never re-fire notifications, per spec."""
        handler = self.handler
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        follow = Follow.objects.create(user=follower, project=project)
        FollowedChannel.objects.create(follow=follow, channel=channel)
        article = ArticleFactory(project=project, channel=channel)
        handler.publish(article.id)
        # Clear any rows from publish-time fan-out so this test is unambiguous.
        Notification.objects.filter(recipient=follower).delete()

        handler.update_article(article.id, published_at=timezone.now())

        assert not Notification.objects.filter(recipient=follower).exists()

    def test_unknown_article_raises(self):
        with pytest.raises(ArticleNotFoundError):
            self.handler.update_article(uuid.uuid4(), title="x")


@pytest.mark.django_db
class TestPublish:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_publishes_and_assigns_slug(self):
        article = ArticleFactory()

        result = self.handler.publish(article.id)

        assert result.state == ArticleState.PUBLISHED
        assert result.published_at is not None
        assert result.slug == "hello-world"

    def test_slug_collision_appends_suffix(self):
        project = ProjectFactory()
        # First publish takes the natural slug.
        a1 = ArticleFactory(project=project)
        self.handler.publish(a1.id)

        a2 = ArticleFactory(project=project)
        self.handler.publish(a2.id)

        slugs = sorted(
            Article.objects.filter(project=project).values_list("slug", flat=True)
        )
        assert slugs == ["hello-world", "hello-world-2"]

    def test_slug_uniqueness_is_per_project(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        a1 = ArticleFactory(project=project_a)
        a2 = ArticleFactory(project=project_b)

        self.handler.publish(a1.id)
        self.handler.publish(a2.id)

        a1.refresh_from_db()
        a2.refresh_from_db()
        assert a1.slug == "hello-world"
        assert a2.slug == "hello-world"

    def test_slug_stable_across_title_edits(self):
        article = ArticleFactory()
        self.handler.publish(article.id)
        original_slug = Article.objects.get(pk=article.id).slug

        self.handler.update_article(article.id, title="Renamed entirely")

        assert Article.objects.get(pk=article.id).slug == original_slug

    def test_rejects_publish_without_title(self):
        project = ProjectFactory()
        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=ChannelFactory(project=project).id,
            author_id=project.creator.id,
            body="x",
            hero_image_id=ProjectImageFactory(project=project).id,
        )

        with pytest.raises(ArticleNotPublishableError):
            self.handler.publish(article.id)

        assert Article.objects.get(pk=article.id).state == ArticleState.DRAFT

    def test_rejects_publish_without_body(self):
        project = ProjectFactory()
        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=ChannelFactory(project=project).id,
            author_id=project.creator.id,
            title="x",
            hero_image_id=ProjectImageFactory(project=project).id,
        )

        with pytest.raises(ArticleNotPublishableError):
            self.handler.publish(article.id)

    def test_rejects_publish_without_hero_image(self):
        project = ProjectFactory()
        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=ChannelFactory(project=project).id,
            author_id=project.creator.id,
            title="x",
            body="y",
        )

        with pytest.raises(ArticleNotPublishableError):
            self.handler.publish(article.id)

    def test_trusted_author_gets_auto_visibility(self):
        author = UserFactory(article_trust=True)
        project = ProjectFactory(owner=author)
        article = ArticleFactory(project=project, author=author)

        result = self.handler.publish(article.id)

        assert result.global_visibility == ArticleGlobalVisibility.AUTO
        assert result.is_globally_visible is True

    def test_untrusted_author_lands_in_pending(self):
        author = UserFactory(article_trust=False)
        project = ProjectFactory(owner=author)
        article = ArticleFactory(project=project, author=author)

        result = self.handler.publish(article.id)

        assert result.global_visibility == ArticleGlobalVisibility.PENDING
        assert result.is_globally_visible is False

    def test_backdated_publish_does_not_fan_out(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        follow = Follow.objects.create(user=follower, project=project)
        FollowedChannel.objects.create(follow=follow, channel=channel)
        article = ArticleFactory(project=project, channel=channel)

        self.handler.publish(
            article.id, published_at=timezone.now() - timedelta(days=7)
        )

        assert not Notification.objects.filter(recipient=follower).exists()

    def test_live_publish_invokes_notification_handler(self):
        article = ArticleFactory()

        with patch(
            "services.notifications.django_impl.handler"
            ".DjangoNotificationHandler.create_notifications_for_article"
        ) as fan_out:
            self.handler.publish(article.id)

        fan_out.assert_called_once_with(article.id)


@pytest.mark.django_db
class TestDelete:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_delete_cascades_notifications(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        follow = Follow.objects.create(user=follower, project=project)
        FollowedChannel.objects.create(follow=follow, channel=channel)
        article = ArticleFactory(project=project, channel=channel)
        self.handler.publish(article.id)
        assert Notification.objects.filter(article=article).exists()

        self.handler.delete_article(article.id)

        assert not Article.objects.filter(pk=article.id).exists()
        assert not Notification.objects.filter(article_id=article.id).exists()

    def test_delete_unknown_article_raises(self):
        with pytest.raises(ArticleNotFoundError):
            self.handler.delete_article(uuid.uuid4())


@pytest.mark.django_db
class TestSetGlobalVisibility:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_pending_to_approved(self):
        author = UserFactory(article_trust=False)
        project = ProjectFactory(owner=author)
        article = ArticleFactory(project=project, author=author)
        self.handler.publish(article.id)
        # Sanity: starts pending.
        assert (
            Article.objects.get(pk=article.id).global_visibility
            == ArticleGlobalVisibility.PENDING
        )

        result = self.handler.set_global_visibility(
            article.id, ArticleGlobalVisibility.APPROVED
        )

        assert result.global_visibility == ArticleGlobalVisibility.APPROVED
        assert result.is_globally_visible is True

    def test_auto_to_demoted_hides_globally(self):
        article = ArticleFactory()
        self.handler.publish(article.id)

        result = self.handler.set_global_visibility(
            article.id, ArticleGlobalVisibility.DEMOTED
        )

        assert result.global_visibility == ArticleGlobalVisibility.DEMOTED
        assert result.is_globally_visible is False
        # Row still exists.
        assert Article.objects.filter(pk=article.id).exists()

    def test_invalid_value_raises(self):
        article = ArticleFactory()
        with pytest.raises(ValueError, match="invalid global_visibility"):
            self.handler.set_global_visibility(article.id, "not-a-state")

    def test_unchanged_value_is_idempotent(self):
        article = ArticleFactory()
        self.handler.publish(article.id)
        article.refresh_from_db()
        # Should not raise; should not roll back to a different state.
        result = self.handler.set_global_visibility(
            article.id, article.global_visibility
        )
        assert result.global_visibility == article.global_visibility


@pytest.mark.django_db
class TestTrustFlagAndExistingArticles:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_flipping_trust_does_not_change_existing_articles(self):
        author = UserFactory(article_trust=True)
        project = ProjectFactory(owner=author)
        article = ArticleFactory(project=project, author=author)
        self.handler.publish(article.id)
        assert (
            Article.objects.get(pk=article.id).global_visibility
            == ArticleGlobalVisibility.AUTO
        )

        author.article_trust = False
        author.save(update_fields=["article_trust"])

        assert (
            Article.objects.get(pk=article.id).global_visibility
            == ArticleGlobalVisibility.AUTO
        )

    def test_cadence_snapshot_unaffected_here(self):
        """Sanity: publish does not mutate the author's cadence."""
        author = UserFactory(article_email_frequency=ArticleEmailFrequency.DAILY)
        project = ProjectFactory(owner=author)
        article = ArticleFactory(project=project, author=author)

        self.handler.publish(article.id)

        author.refresh_from_db()
        assert author.article_email_frequency == ArticleEmailFrequency.DAILY


@pytest.mark.django_db
class TestArticleSummary:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_new_article_has_empty_summary(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project)

        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
        )

        assert article.summary == ""

    def test_update_sets_summary(self):
        article = ArticleFactory(body="The body opening.")

        updated = self.handler.update_article(article.id, summary="A hook.")

        assert updated.summary == "A hook."

    def test_empty_string_clears_the_summary(self):
        article = ArticleFactory(summary="A hook.")

        updated = self.handler.update_article(article.id, summary="")

        assert updated.summary == ""

    def test_omitting_summary_leaves_it_alone(self):
        article = ArticleFactory(summary="A hook.")

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.summary == "A hook."


@pytest.mark.django_db
class TestUpdateHeroImage:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_omitting_hero_image_id_leaves_the_hero_alone(self):
        article = ArticleFactory()
        original_hero_id = article.hero_image_id

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.hero_image_id == original_hero_id

    def test_explicit_none_clears_the_hero_on_a_draft(self):
        article = ArticleFactory()
        assert article.hero_image_id is not None

        updated = self.handler.update_article(article.id, hero_image_id=None)

        updated.refresh_from_db()
        assert updated.hero_image_id is None

    def test_explicit_none_on_a_published_article_is_rejected(self):
        article = PublishedArticleFactory(slug="a-post")
        original_hero_id = article.hero_image_id

        with pytest.raises(PublishedArticleNeedsHeroImageError):
            self.handler.update_article(article.id, hero_image_id=None)

        article.refresh_from_db()
        assert article.hero_image_id == original_hero_id

    def test_swapping_the_hero_on_a_published_article_is_allowed(self):
        article = PublishedArticleFactory(slug="a-post")
        replacement = ProjectImageFactory(project=article.project)

        updated = self.handler.update_article(article.id, hero_image_id=replacement.id)

        assert updated.hero_image_id == replacement.id
