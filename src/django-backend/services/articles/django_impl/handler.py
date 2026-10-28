from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.articles.models import (
    Article,
    ArticleGlobalVisibility,
    ArticleSource,
    ArticleState,
)
from apps.articles.slugs import assign_unique_article_slug
from apps.follows.models import PERSONAL_CHANNEL_NAME, Channel
from apps.projects.models import Image
from services.articles import crop
from services.articles.django_impl.query import article_detail_queryset
from services.articles.exceptions import (
    ArticleNotFoundError,
    ArticleNotPublishableError,
    ChannelHasArticlesError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    DuplicateChannelNameError,
    InvalidCropError,
    LastChannelError,
    ListingImageNotUploadedError,
    ListingImageOnWrongProjectError,
    NoChannelForAuthorArticleError,
)
from services.articles.handler_interface import (
    UNSET,
    ArticleHandlerInterface,
    UnsetType,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

logger = logging.getLogger(__name__)


def _is_backdated(approved_at: datetime | None) -> bool:
    """True when an article became visible more than 60s ago.

    Reads `approved_at`, not `published_at`. The two agree on a straight publish
    by a trusted author, but nowhere else: an importer sets `published_at` to
    whenever the article is from, and an article held for review carries a
    `published_at` as old as the admin's queue. Measuring the fan-out against
    that suppressed the notification for every article a human took longer than
    a minute to approve — which is all of them.
    """
    if approved_at is None:
        return False
    return approved_at < timezone.now() - timedelta(seconds=60)


def _enqueue_fan_out(article: Article) -> None:
    # Local import: api.tasks reaches back into the service layer.
    from api.tasks.notifications import (  # noqa: PLC0415
        create_article_notifications,
    )

    # `str`, not `UUID`: the DatabaseBackend serialises task arguments through
    # `normalize_json`, which a bare UUID does not survive.
    create_article_notifications.enqueue(str(article.id))


def _resolve_visibility_on_publish(article: Article) -> str:
    if article.source == ArticleSource.EXTERNAL:
        # Phase 6 governance: external articles route via feed approval state,
        # not the author's trust flag (the author may not even be a User).
        # Until Phase 6 lands, this branch is unreachable from the API path.
        return ArticleGlobalVisibility.PENDING
    if article.author and article.author.article_trust:
        return ArticleGlobalVisibility.AUTO
    return ArticleGlobalVisibility.PENDING


class DjangoArticleHandler(ArticleHandlerInterface):
    # ------------------------------------------------------------------
    # Articles
    # ------------------------------------------------------------------

    def create_draft(
        self,
        *,
        author_id: UUID,
        project_id: UUID | None = None,
        channel_id: UUID | None = None,
        title: str = "",
        body: str = "",
    ) -> Article:
        if (project_id is None) != (channel_id is None):
            msg = "a project draft needs a channel; an author-owned draft has none"
            raise ValueError(msg)
        channel = (
            self._resolve_channel_on_project(channel_id, project_id)
            if project_id is not None
            else None
        )
        # No cover on create: an image cannot be uploaded against an article
        # that does not exist yet.
        article = Article(
            project_id=project_id,
            channel=channel,
            author_id=author_id,
            title=title,
            body=body,
            source=ArticleSource.INTERNAL,
            state=ArticleState.DRAFT,
        )
        article.save()
        return article

    def update_article(
        self,
        article_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        summary: str | None = None,
        listing_image_id: UUID | None | UnsetType = UNSET,
        listing_crop: dict[str, float] | None | UnsetType = UNSET,
        channel_id: UUID | None = None,
        published_at: datetime | None = None,
    ) -> Article:
        article = self._get_article(article_id)
        update_fields: list[str] = []

        if title is not None and title != article.title:
            article.title = title
            update_fields.append("title")
        if body is not None and body != article.body:
            article.body = body
            update_fields.append("body")
        if summary is not None and summary != article.summary:
            article.summary = summary
            update_fields.append("summary")
        update_fields += self._apply_listing_image(
            article,
            listing_image_id=listing_image_id,
            listing_crop=listing_crop,
        )
        if channel_id is not None and channel_id != article.channel_id:
            if article.is_author_owned:
                raise NoChannelForAuthorArticleError
            channel = self._resolve_channel_on_project(channel_id, article.project_id)
            article.channel = channel
            update_fields.append("channel")
        if published_at is not None and published_at != article.published_at:
            # Editing published_at after publish is allowed but NEVER fires
            # retroactive notifications (per spec).
            article.published_at = published_at
            update_fields.append("published_at")

        if update_fields:
            article.save(update_fields=update_fields)
        return article

    def publish(
        self,
        article_id: UUID,
        *,
        published_at: datetime | None = None,
    ) -> Article:
        article = self._get_article(article_id)

        if not article.title or not article.body:
            raise ArticleNotPublishableError

        effective_published_at = published_at or timezone.now()

        with transaction.atomic():
            update_fields = [
                "state",
                "published_at",
                "global_visibility",
                "approved_at",
            ]
            if article.is_author_owned and article.channel_id is None:
                # The person's one channel, made on their first publish. Its
                # `post_save` enrols everyone already following the person, so
                # by the time the fan-out task runs the rows it selects exist.
                article.channel = self._personal_channel(article.author_id)
                update_fields.append("channel")
            article.state = ArticleState.PUBLISHED
            article.published_at = effective_published_at
            article.global_visibility = _resolve_visibility_on_publish(article)
            # A publish that is visible immediately is its own approval, and it
            # takes the publish time rather than `now` so a backdated import
            # stays backdated: the fan-out reads this field. An article held for
            # review is not approved yet and keeps a null until an admin says so.
            if article.is_globally_visible:
                article.approved_at = effective_published_at
            article.save(update_fields=update_fields)
            if article.slug is None:
                assign_unique_article_slug(article)
            if article.is_globally_visible and not _is_backdated(article.approved_at):
                # Fan-out is ~2N queries on a house-channel publish, so it goes
                # to the worker rather than the request. Enqueued *inside* the
                # transaction on purpose: the queue is a table
                # (django-tasks-db), so the task row and the PUBLISHED write
                # commit together — a worker cannot see the task before the
                # article, and a crash cannot lose the enqueue. `on_commit`
                # would reopen that window.
                #
                # The backdating guard stays here: the task only gets an id,
                # and from the row alone a backdated publish and a live publish
                # the worker was slow to reach look identical.
                #
                # An article held for review notifies nobody yet — the link
                # would 404 for every recipient. set_global_visibility picks the
                # fan-out up when an admin approves it.
                _enqueue_fan_out(article)

        return article

    def delete_article(self, article_id: UUID) -> None:
        deleted, _ = Article.objects.filter(pk=article_id).delete()
        if not deleted:
            raise ArticleNotFoundError

    def set_global_visibility(self, article_id: UUID, value: str) -> Article:
        if value not in {choice.value for choice in ArticleGlobalVisibility}:
            msg = f"invalid global_visibility value: {value!r}"
            raise ValueError(msg)
        article = self._get_article(article_id)
        if article.global_visibility == value:
            return article

        was_visible = article.is_globally_visible
        with transaction.atomic():
            article.global_visibility = value
            fields = ["global_visibility"]
            # Approval is the moment the article becomes news, whatever date it
            # carries, so the clock the fan-out reads starts here. Stamped only
            # on the transition into visibility — a demotion leaves the last
            # approval where it was rather than pretending it never happened.
            became_visible = not was_visible and article.is_globally_visible
            if became_visible:
                article.approved_at = timezone.now()
                fields.append("approved_at")
            article.save(update_fields=fields)
            # Becoming visible is when this article's followers can finally read
            # it, so it is where the fan-out publish held back happens. Safe to
            # re-run: the fan-out is get_or_create per (recipient, article), so a
            # demote-then-approve delivers nothing twice.
            #
            # The feed needs no equivalent hook — its read filter reads the same
            # visibility, in both directions.
            #
            # No backdating guard here, unlike the publish path: `approved_at`
            # was just set to now, so there is nothing for one to catch. An
            # approval is news now whatever date the article carries — an import
            # that should notify nobody arrives already visible and is suppressed
            # on the publish path instead. See
            # `TestFanOutOnApproval.test_a_backdated_article_approved_now_is_news_now`.
            if became_visible:
                _enqueue_fan_out(article)
        return article

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------

    def add_channel(self, project_id: UUID, name: str) -> Channel:
        try:
            return Channel.objects.create(project_id=project_id, name=name)
        except IntegrityError as exc:
            raise DuplicateChannelNameError from exc

    def rename_channel(self, channel_id: UUID, new_name: str) -> Channel:
        try:
            channel = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc
        if channel.name == new_name:
            return channel
        channel.name = new_name
        try:
            channel.save(update_fields=["name"])
        except IntegrityError as exc:
            raise DuplicateChannelNameError from exc
        return channel

    def delete_channel(self, channel_id: UUID) -> None:
        try:
            channel = Channel.objects.select_related("project").get(pk=channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc

        article_count = Article.objects.filter(channel=channel).count()
        if article_count:
            raise ChannelHasArticlesError(article_count)

        # A person's channel is not managed: it is their only one, and the
        # project endpoints that reach here never resolve it. The guard holds
        # for it as well — the count is one.
        sibling_count = Channel.objects.filter(
            project=channel.project, owner=channel.owner
        ).count()
        if sibling_count <= 1:
            raise LastChannelError

        channel.delete()

    def bulk_reassign_articles(
        self,
        source_channel_id: UUID,
        target_channel_id: UUID,
    ) -> int:
        try:
            source = Channel.objects.get(pk=source_channel_id)
            target = Channel.objects.get(pk=target_channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc
        if source.project_id != target.project_id:
            raise ChannelOnWrongProjectError
        return Article.objects.filter(channel=source).update(channel=target)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_listing_image(
        self,
        article: Article,
        *,
        listing_image_id: UUID | None | UnsetType,
        listing_crop: dict[str, float] | None | UnsetType,
    ) -> list[str]:
        """Settle the cover and its crop; return the fields touched.

        UNSET leaves a value alone. A rectangle drawn on one image means
        nothing on another, so an image that changed or went away takes its
        framing with it unless a new crop came with the request.
        """
        if listing_image_id is UNSET:
            image = article.listing_image
        else:
            image = self._resolve_listing_image(listing_image_id, article)
        image_changed = (image.pk if image else None) != article.listing_image_id

        if listing_crop is not UNSET:
            rect = self._validated_crop(listing_crop, image)
        elif image_changed:
            rect = None
        else:
            rect = article.listing_crop

        touched: list[str] = []
        if image_changed:
            article.listing_image = image
            touched.append("listing_image")
        if rect != article.listing_crop:
            article.listing_crop = rect
            touched.append("listing_crop")
        return touched

    def _validated_crop(
        self,
        value: dict[str, float] | None,
        image: Image | None,
    ) -> dict[str, float] | None:
        """Normalise an incoming crop, or raise ``InvalidCropError``."""
        if value is None:
            return None
        if image is None:
            raise InvalidCropError(crop.NO_LISTING_IMAGE)

        rect = crop.parse_crop(value)
        if rect is None:
            raise InvalidCropError(crop.MALFORMED)
        crop.validate_crop(rect, width=image.width, height=image.height)
        return rect.to_dict()

    def _get_article(self, article_id: UUID) -> Article:
        try:
            return article_detail_queryset().get(pk=article_id)
        except Article.DoesNotExist as exc:
            raise ArticleNotFoundError from exc

    def _resolve_channel_on_project(
        self, channel_id: UUID, project_id: UUID
    ) -> Channel:
        try:
            channel = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc
        if channel.project_id != project_id:
            raise ChannelOnWrongProjectError
        return channel

    @staticmethod
    def _personal_channel(author_id: UUID) -> Channel:
        channel, _ = Channel.objects.get_or_create(
            owner_id=author_id, name=PERSONAL_CHANNEL_NAME
        )
        return channel

    def _resolve_listing_image(
        self, listing_image_id: UUID | None, article: Article
    ) -> Image | None:
        """The image `listing_image_id` names, if the article may use it.

        A project article may use any of its project's images — the gallery
        as well as its own uploads. An author-owned article has only its own.
        """
        if listing_image_id is None:
            return None
        try:
            image = Image.objects.get(pk=listing_image_id)
        except Image.DoesNotExist as exc:
            raise ListingImageOnWrongProjectError from exc
        if article.is_author_owned:
            if image.article_id != article.id:
                raise ListingImageOnWrongProjectError
        elif image.project_id != article.project_id:
            raise ListingImageOnWrongProjectError
        if not image.is_uploaded:
            # Distinct from the wrong-project case: the id is one the client
            # legitimately holds — it comes back from `upload-url` — but the
            # PUT behind it never landed, so the card would render broken.
            raise ListingImageNotUploadedError
        return image
