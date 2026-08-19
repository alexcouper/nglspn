from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from api.schemas.article import ArticleOut
from apps.articles.models import (
    Article,
    ArticleGlobalVisibility,
    ArticleSource,
    ArticleState,
    ListingImageMode,
)
from apps.follows.models import Follow, FollowedChannel
from apps.notifications.models import Notification
from apps.projects.models import ProjectImage, UploadStatus
from apps.users.models import ArticleEmailFrequency
from services.articles.crop import CARD_RATIO
from services.articles.django_impl.handler import DjangoArticleHandler
from services.articles.exceptions import (
    ArticleNotFoundError,
    ArticleNotPublishableError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    ListingImageNotUploadedError,
    ListingImageOnWrongProjectError,
)
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
    UserFactory,
    article_image,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _crop(x: float = 0.1, y: float = 0.2, w: float = 0.6) -> dict[str, float]:
    """A 16:9 crop of a square source."""
    return {"x": x, "y": y, "w": w, "h": w / CARD_RATIO, "ratio": CARD_RATIO}


@contextmanager
def _patched_enqueue():
    """Stop the fan-out task at the queue boundary, yielding its `enqueue` mock.

    The test settings pin `ImmediateBackend`, which runs the task body inline,
    so without this a query count over `publish` measures the fan-out too. The
    whole `Task` is replaced rather than its `enqueue` attribute because `Task`
    is a frozen dataclass and `patch` cannot unset an attribute on one.
    """
    with patch("api.tasks.notifications.create_article_notifications") as fan_out_task:
        yield fan_out_task.enqueue


def _follow_channel_from_new_users(project, channel, *, count: int) -> None:
    for _ in range(count):
        follow = Follow.objects.create(user=UserFactory(), project=project)
        FollowedChannel.objects.create(follow=follow, channel=channel)


def _count_queries(work: Callable[[], object]) -> int:
    with CaptureQueriesContext(connection) as queries:
        work()
    return len(queries)


def _article_with_figures(count: int) -> Article:
    article = ArticleFactory()
    for _ in range(count):
        article_image(article)
    return article


def _save_and_serialise(handler: DjangoArticleHandler, article_id) -> None:
    """What a *Save draft* actually costs: the write plus the response body."""
    article = handler.update_article(article_id, title="Edited")
    ArticleOut.from_orm(article)


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
        assert article.listing_image_id is None
        assert article.listing_image_mode == ListingImageMode.AUTO
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
class TestSaveDraftQueryCount:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_does_not_query_per_article_figure(self):
        # `ArticleOut.from_orm` is the load-bearing half: the cost is in
        # serialising `images` and their variants, not in the handler, so a
        # count over `update_article` alone would pass without the prefetch.
        one = _article_with_figures(1)
        twelve = _article_with_figures(12)

        one_figure = _count_queries(lambda: _save_and_serialise(self.handler, one.id))
        twelve_figures = _count_queries(
            lambda: _save_and_serialise(self.handler, twelve.id)
        )

        assert twelve_figures == one_figure


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
        )

        with pytest.raises(ArticleNotPublishableError):
            self.handler.publish(article.id)

    def test_publishes_without_an_image(self):
        project = ProjectFactory()
        article = self.handler.create_draft(
            project_id=project.id,
            channel_id=ChannelFactory(project=project).id,
            author_id=project.creator.id,
            title="x",
            body="y",
        )

        published = self.handler.publish(article.id)

        assert published.state == ArticleState.PUBLISHED
        assert published.listing_image_id is None

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

    def test_backdated_publish_dates_the_approval_to_the_publish(self):
        """The import story rests on this field, not on `published_at`.

        An article brought in with its own old date arrives already visible, and
        `approved_at` has to carry that date rather than now: it is the only
        thing the fan-out reads to decide the article is not news. Approving
        through the review queue instead always stamps now and does notify —
        see `TestFanOutOnApproval.test_a_backdated_article_approved_now_is_news_now`.
        """
        backdated = timezone.now() - timedelta(days=7)
        article = ArticleFactory()

        published = self.handler.publish(article.id, published_at=backdated)

        assert published.is_globally_visible is True
        assert published.approved_at == backdated

    def test_live_publish_enqueues_the_fan_out_task(self):
        article = ArticleFactory()

        with _patched_enqueue() as enqueue:
            self.handler.publish(article.id)

        # `str`, not `UUID`: the DatabaseBackend serialises task arguments
        # through `normalize_json` and a bare UUID does not survive it. The
        # ImmediateBackend used in tests would accept one silently.
        enqueue.assert_called_once_with(str(article.id))

    def test_backdated_publish_enqueues_nothing(self):
        article = ArticleFactory()

        with _patched_enqueue() as enqueue:
            self.handler.publish(
                article.id, published_at=timezone.now() - timedelta(days=7)
            )

        enqueue.assert_not_called()

    def test_a_failed_publish_write_enqueues_nothing(self):
        article = ArticleFactory()

        with (
            _patched_enqueue() as enqueue,
            patch.object(Article, "save", side_effect=IntegrityError),
            pytest.raises(IntegrityError),
        ):
            self.handler.publish(article.id)

        enqueue.assert_not_called()

    def test_publish_awaiting_review_enqueues_nothing(self):
        """A follower notified now would land on a 404 until an admin approves."""
        author = UserFactory(article_trust=False)
        article = ArticleFactory(project=ProjectFactory(owner=author), author=author)

        with _patched_enqueue() as enqueue:
            self.handler.publish(article.id)

        enqueue.assert_not_called()


@pytest.mark.django_db
class TestPublishQueryCount:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_does_not_query_per_follower(self):
        """The fan-out is O(N) by nature, so publish itself must not carry it."""
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        _follow_channel_from_new_users(project, channel, count=1)
        # Distinct titles: two articles sharing one would differ by the extra
        # `.exists()` the slug collision loop costs, which is not what this
        # test is about.
        one = ArticleFactory(project=project, channel=channel, title="First")
        twenty = ArticleFactory(project=project, channel=channel, title="Second")

        with _patched_enqueue():
            one_follower = _count_queries(lambda: self.handler.publish(one.id))
            _follow_channel_from_new_users(project, channel, count=19)
            twenty_followers = _count_queries(lambda: self.handler.publish(twenty.id))

        assert twenty_followers == one_follower


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
class TestFanOutOnApproval:
    """Publish holds the fan-out back while an article is invisible, so approval
    is where its followers finally hear about it.
    """

    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def _publish_awaiting_review(self) -> Article:
        author = UserFactory(article_trust=False)
        article = ArticleFactory(project=ProjectFactory(owner=author), author=author)
        with _patched_enqueue():
            return self.handler.publish(article.id)

    def test_approving_enqueues_the_fan_out_task(self):
        article = self._publish_awaiting_review()

        with _patched_enqueue() as enqueue:
            self.handler.set_global_visibility(
                article.id, ArticleGlobalVisibility.APPROVED
            )

        enqueue.assert_called_once_with(str(article.id))

    def test_approving_long_after_the_publish_still_fans_out(self):
        """Review takes as long as it takes, and the article is news when it
        clears — measuring its age from `published_at` suppressed the fan-out
        for anything an admin did not get to within a minute, which is all of
        them.
        """
        article = self._publish_awaiting_review()
        Article.objects.filter(pk=article.pk).update(
            published_at=timezone.now() - timedelta(days=7)
        )

        with _patched_enqueue() as enqueue:
            self.handler.set_global_visibility(
                article.id, ArticleGlobalVisibility.APPROVED
            )

        enqueue.assert_called_once_with(str(article.id))

    def test_approving_stamps_the_approval_time(self):
        article = self._publish_awaiting_review()
        assert article.approved_at is None
        before = timezone.now()

        approved = self.handler.set_global_visibility(
            article.id, ArticleGlobalVisibility.APPROVED
        )

        assert before <= approved.approved_at <= timezone.now()

    def test_demoting_leaves_the_approval_time_alone(self):
        article = ArticleFactory()
        with _patched_enqueue():
            published = self.handler.publish(article.id)
        approved_at = published.approved_at

        demoted = self.handler.set_global_visibility(
            article.id, ArticleGlobalVisibility.DEMOTED
        )

        assert demoted.approved_at == approved_at

    def test_demoting_enqueues_nothing(self):
        article = ArticleFactory()
        with _patched_enqueue():
            self.handler.publish(article.id)

        with _patched_enqueue() as enqueue:
            self.handler.set_global_visibility(
                article.id, ArticleGlobalVisibility.DEMOTED
            )

        enqueue.assert_not_called()

    def test_a_draft_moved_to_approved_enqueues_nothing(self):
        """`global_visibility` is settable on an unpublished article. It has no
        audience until it publishes, and publish will do the enqueue itself.
        """
        article = ArticleFactory()

        with _patched_enqueue() as enqueue:
            self.handler.set_global_visibility(
                article.id, ArticleGlobalVisibility.APPROVED
            )

        enqueue.assert_not_called()

    def test_a_backdated_article_approved_now_is_news_now(self):
        """The one case that changed hands when the clock moved to `approved_at`.

        A seven-day-old `published_at` used to suppress this. It no longer does,
        and should not: an admin approving today is publishing it today, and the
        date on the article says only what it is about. An import that genuinely
        should notify nobody arrives already visible and is suppressed on the
        publish path, where its old `approved_at` is set — see
        `TestPublishFanOut.test_backdated_publish_enqueues_nothing`.
        """
        author = UserFactory(article_trust=False)
        article = ArticleFactory(project=ProjectFactory(owner=author), author=author)
        with _patched_enqueue():
            self.handler.publish(
                article.id, published_at=timezone.now() - timedelta(days=7)
            )

        with _patched_enqueue() as enqueue:
            self.handler.set_global_visibility(
                article.id, ArticleGlobalVisibility.APPROVED
            )

        enqueue.assert_called_once_with(str(article.id))

    def test_re_approving_notifies_each_follower_once(self):
        """The fan-out is idempotent per (recipient, article), so a demote and a
        second approval must not deliver the article twice.
        """
        author = UserFactory(article_trust=False)
        project = ProjectFactory(owner=author)
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        follow = Follow.objects.create(user=follower, project=project)
        FollowedChannel.objects.create(follow=follow, channel=channel)
        article = ArticleFactory(project=project, channel=channel, author=author)
        self.handler.publish(article.id)

        for value in (
            ArticleGlobalVisibility.APPROVED,
            ArticleGlobalVisibility.DEMOTED,
            ArticleGlobalVisibility.APPROVED,
        ):
            self.handler.set_global_visibility(article.id, value)

        delivered = Notification.objects.filter(
            recipient=follower, article=article
        ).count()
        assert delivered == 1


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
class TestListingImageAutoMode:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_adopts_the_earliest_upload_on_save(self):
        article = ArticleFactory()
        first = article_image(article)
        article_image(article)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id == first.id
        assert updated.listing_crop is None
        assert updated.listing_image_mode == ListingImageMode.AUTO

    def test_orders_by_upload_time_not_display_order(self):
        # An article's uploads all take display_order from the project's
        # non-article image count, so Meta.ordering cannot break the tie.
        article = ArticleFactory()
        first = article_image(article, display_order=7)
        article_image(article, display_order=0)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id == first.id

    def test_a_later_upload_does_not_displace_it(self):
        article = ArticleFactory()
        first = article_image(article)
        self.handler.update_article(article.id, title="One")

        article_image(article)
        updated = self.handler.update_article(article.id, title="Two")

        assert updated.listing_image_id == first.id

    def test_deleting_the_first_promotes_the_next(self):
        article = ArticleFactory()
        first = article_image(article)
        second = article_image(article)
        self.handler.update_article(article.id, title="One")

        first.delete()
        updated = self.handler.update_article(article.id, title="Two")

        assert updated.listing_image_id == second.id

    def test_stays_null_with_no_linked_images(self):
        article = ArticleFactory()
        ProjectImageFactory(project=article.project)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id is None
        assert updated.listing_image_mode == ListingImageMode.AUTO

    def test_skips_an_upload_that_never_completed(self):
        # The row is created before the S3 PUT and nothing deletes it when the
        # PUT fails, so the earliest row is not necessarily a usable image.
        article = ArticleFactory()
        article_image(article, upload_status=UploadStatus.PENDING)
        completed = article_image(article)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id == completed.id

    def test_skips_a_failed_upload(self):
        article = ArticleFactory()
        article_image(article, upload_status=UploadStatus.FAILED)
        completed = article_image(article)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id == completed.id

    def test_stays_null_when_every_upload_is_incomplete(self):
        article = ArticleFactory()
        article_image(article, upload_status=UploadStatus.PENDING)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id is None


@pytest.mark.django_db
class TestListingImageChoice:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_choosing_an_image_commits_the_mode(self):
        article = ArticleFactory()
        article_image(article)
        chosen = article_image(article)

        updated = self.handler.update_article(article.id, listing_image_id=chosen.id)

        assert updated.listing_image_id == chosen.id
        assert updated.listing_image_mode == ListingImageMode.CHOSEN

    def test_a_chosen_image_is_not_re_derived_on_a_later_save(self):
        article = ArticleFactory()
        article_image(article)
        chosen = article_image(article)
        self.handler.update_article(article.id, listing_image_id=chosen.id)

        updated = self.handler.update_article(article.id, title="New title")

        assert updated.listing_image_id == chosen.id

    def test_adjusting_only_the_crop_commits_the_choice(self):
        article = ArticleFactory()
        first = article_image(article, width=4000, height=4000)
        self.handler.update_article(article.id, title="One")

        updated = self.handler.update_article(article.id, listing_crop=_crop())

        assert updated.listing_image_mode == ListingImageMode.CHOSEN
        assert updated.listing_image_id == first.id
        assert updated.listing_crop["ratio"] == pytest.approx(CARD_RATIO, abs=1e-4)

    def test_a_new_image_drops_a_crop_drawn_on_the_old_one(self):
        article = ArticleFactory()
        first = article_image(article, width=4000, height=4000)
        replacement = article_image(article, width=4000, height=4000)
        self.handler.update_article(
            article.id, listing_image_id=first.id, listing_crop=_crop()
        )

        updated = self.handler.update_article(
            article.id, listing_image_id=replacement.id
        )

        assert updated.listing_image_id == replacement.id
        assert updated.listing_crop is None

    def test_rejects_an_image_on_another_project(self):
        article = ArticleFactory()
        foreign = ProjectImageFactory(project=ProjectFactory())

        with pytest.raises(ListingImageOnWrongProjectError):
            self.handler.update_article(article.id, listing_image_id=foreign.id)

    def test_rejects_an_upload_that_never_completed(self):
        article = ArticleFactory()
        pending = article_image(article, upload_status=UploadStatus.PENDING)

        with pytest.raises(ListingImageNotUploadedError):
            self.handler.update_article(article.id, listing_image_id=pending.id)

    def test_rejects_a_failed_upload(self):
        article = ArticleFactory()
        failed = article_image(article, upload_status=UploadStatus.FAILED)

        with pytest.raises(ListingImageNotUploadedError):
            self.handler.update_article(article.id, listing_image_id=failed.id)

    def test_clearing_the_image_on_a_published_article_is_allowed(self):
        article = PublishedArticleFactory(slug="a-post")
        article_image(article)
        self.handler.update_article(article.id, title="One")

        updated = self.handler.update_article(
            article.id,
            listing_image_id=None,
            listing_image_mode=ListingImageMode.NONE,
        )

        assert updated.listing_image_id is None


@pytest.mark.django_db
class TestListingImageRemoval:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_removal_survives_later_saves(self):
        article = ArticleFactory()
        article_image(article)
        self.handler.update_article(article.id, title="One")

        self.handler.update_article(
            article.id,
            listing_image_id=None,
            listing_image_mode=ListingImageMode.NONE,
        )
        updated = self.handler.update_article(article.id, title="Two")

        assert updated.listing_image_id is None
        assert updated.listing_image_mode == ListingImageMode.NONE

    def test_returning_to_auto_re_adopts_the_first_upload(self):
        article = ArticleFactory()
        first = article_image(article)
        self.handler.update_article(
            article.id,
            listing_image_id=None,
            listing_image_mode=ListingImageMode.NONE,
        )

        updated = self.handler.update_article(
            article.id, listing_image_mode=ListingImageMode.AUTO
        )

        assert updated.listing_image_id == first.id


@pytest.mark.django_db
class TestImageArticleLink:
    def setup_method(self):
        self.handler = DjangoArticleHandler()

    def test_deleting_an_article_deletes_its_images(self):
        article = ArticleFactory()
        image = article_image(article)
        project_image = ProjectImageFactory(project=article.project)

        self.handler.delete_article(article.id)

        assert not ProjectImage.objects.filter(pk=image.id).exists()
        assert ProjectImage.objects.filter(pk=project_image.id).exists()

    def test_deleting_the_listing_image_blanks_it_rather_than_raising(self):
        article = ArticleFactory()
        image = article_image(article)
        self.handler.update_article(article.id, listing_image_id=image.id)

        image.delete()

        article.refresh_from_db()
        assert article.listing_image_id is None
        assert article.listing_image_mode == ListingImageMode.CHOSEN
