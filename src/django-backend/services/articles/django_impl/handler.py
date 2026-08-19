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
    ListingImageMode,
)
from apps.articles.slugs import assign_unique_article_slug
from apps.follows.models import Channel
from apps.projects.models import ProjectImage
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
        project_id: UUID,
        channel_id: UUID,
        author_id: UUID,
        title: str = "",
        body: str = "",
    ) -> Article:
        channel = self._resolve_channel_on_project(channel_id, project_id)
        # No listing image on create: an image cannot be uploaded against an
        # article that does not exist yet, so `auto` has nothing to resolve to.
        article = Article(
            project_id=project_id,
            channel=channel,
            author_id=author_id,
            title=title,
            body=body,
            listing_image_mode=ListingImageMode.AUTO,
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
        listing_image_mode: str | None = None,
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
            listing_image_mode=listing_image_mode,
        )
        if channel_id is not None and channel_id != article.channel_id:
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
            article.state = ArticleState.PUBLISHED
            article.published_at = effective_published_at
            article.global_visibility = _resolve_visibility_on_publish(article)
            # A publish that is visible immediately is its own approval, and it
            # takes the publish time rather than `now` so a backdated import
            # stays backdated: the fan-out reads this field. An article held for
            # review is not approved yet and keeps a null until an admin says so.
            if article.is_globally_visible:
                article.approved_at = effective_published_at
            article.save(
                update_fields=[
                    "state",
                    "published_at",
                    "global_visibility",
                    "approved_at",
                ]
            )
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

        sibling_count = Channel.objects.filter(project=channel.project).count()
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
        listing_image_mode: str | None,
    ) -> list[str]:
        """Settle the listing image, its crop and its mode; return fields touched.

        Called on every update, because ``auto`` is resolved on save rather than
        on read — a listing card is then a plain FK join instead of a per-card
        subquery.
        """
        mode = self._resolve_mode(
            article,
            listing_image_id=listing_image_id,
            listing_crop=listing_crop,
            listing_image_mode=listing_image_mode,
        )

        if mode == ListingImageMode.NONE:
            image: ProjectImage | None = None
            rect: dict[str, float] | None = None
        elif mode == ListingImageMode.AUTO:
            # Read off the prefetch: `.uploaded()` on the related manager would
            # issue a fresh query and throw the prefetch away. `is_uploaded` is
            # the documented in-memory twin of `.uploaded()`, and this is the
            # same filter and sort `ArticleOut.resolve_images` applies, so the
            # wizard's list and `auto`'s pick stay in the same order.
            # `ProjectImage.Meta.ordering` leads with display_order, which is
            # identical across an article's uploads, so order explicitly.
            image = next(
                iter(
                    sorted(
                        (img for img in article.images.all() if img.is_uploaded),
                        key=lambda img: img.created_at,
                    )
                ),
                None,
            )
            rect = None
        else:
            image = self._chosen_image(article, listing_image_id)
            rect = self._chosen_crop(
                article,
                image,
                listing_crop=listing_crop,
                image_changed=(image.pk if image else None) != article.listing_image_id,
            )

        touched: list[str] = []
        if (image.pk if image else None) != article.listing_image_id:
            article.listing_image = image
            touched.append("listing_image")
        if rect != article.listing_crop:
            article.listing_crop = rect
            touched.append("listing_crop")
        if mode != article.listing_image_mode:
            article.listing_image_mode = mode
            touched.append("listing_image_mode")
        return touched

    def _resolve_mode(
        self,
        article: Article,
        *,
        listing_image_id: UUID | None | UnsetType,
        listing_crop: dict[str, float] | None | UnsetType,
        listing_image_mode: str | None,
    ) -> str:
        """An explicit mode wins; otherwise touching the image or its framing
        commits the author's choice, so the next save does not re-derive the
        image out from under a rectangle they just drew.
        """
        if listing_image_mode is not None:
            return listing_image_mode
        if listing_image_id is not UNSET or listing_crop is not UNSET:
            return ListingImageMode.CHOSEN
        return article.listing_image_mode

    def _chosen_image(
        self,
        article: Article,
        listing_image_id: UUID | None | UnsetType,
    ) -> ProjectImage | None:
        if listing_image_id is UNSET:
            return article.listing_image
        return self._resolve_listing_image(listing_image_id, article.project_id)

    def _chosen_crop(
        self,
        article: Article,
        image: ProjectImage | None,
        *,
        listing_crop: dict[str, float] | None | UnsetType,
        image_changed: bool,
    ) -> dict[str, float] | None:
        if listing_crop is not UNSET:
            return self._validated_crop(listing_crop, image)
        # A rectangle drawn on one image means nothing on another, so an image
        # that changed or went away takes its framing with it.
        if image_changed:
            return None
        return article.listing_crop

    def _validated_crop(
        self,
        value: dict[str, float] | None,
        image: ProjectImage | None,
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

    def _resolve_listing_image(
        self, listing_image_id: UUID | None, project_id: UUID
    ) -> ProjectImage | None:
        if listing_image_id is None:
            return None
        try:
            image = ProjectImage.objects.get(pk=listing_image_id)
        except ProjectImage.DoesNotExist as exc:
            raise ListingImageOnWrongProjectError from exc
        if image.project_id != project_id:
            raise ListingImageOnWrongProjectError
        if not image.is_uploaded:
            # Distinct from the wrong-project case: the id is one the client
            # legitimately holds — it comes back from `upload-url` — but the
            # PUT behind it never landed, so the card would render broken.
            raise ListingImageNotUploadedError
        return image
