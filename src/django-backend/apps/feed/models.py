import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.articles.models import globally_visible_q
from apps.projects.models import ProjectStatus


class FeedEventKind(models.TextChoices):
    ARTICLE_PUBLISHED = "article_published", "Article published"
    PROJECT_PUBLISHED = "project_published", "Project published"
    PROJECT_TIPOFF = "project_tipoff", "Community tipoff"
    DISCUSSION_PROMOTED = "discussion_promoted", "Discussion promoted"


class FeedEventQuerySet(models.QuerySet["FeedEvent"]):
    def renderable(self) -> "FeedEventQuerySet":
        """The rows the feed serves right now.

        The clock is part of the filter: an article published with a
        `published_at` still ahead of us has its entry in the table, ordered
        where it belongs, and invisible until its day.
        """
        return self.filter(
            occurred_at__lte=timezone.now(),
            retired_at__isnull=True,
        ).visible_subject()

    def visible_subject(self) -> "FeedEventQuerySet":
        """Drop entries whose subject is no longer shown on the site.

        An entry is appended when a project is approved and nothing withdraws it
        if the project is later rejected or iced. Without this the feed keeps
        publishing that project's title, tagline and icon, and links to a page
        that 404s for everyone but its owner — the rest of the site treats
        anything but APPROVED as invisible.

        An article carries a second gate of its own: an admin can hold it for
        review or demote it after the fact, and the entry has to follow. Filtered
        here rather than maintained on the FeedEvent row, because both directions
        then come out of one rule — approving needs no feed write at all, and the
        `articles` join is already in the query for `article__project__status`
        and for `with_sources()`, so this costs no round trip.
        """
        approved = ProjectStatus.APPROVED
        return self.filter(
            Q(project__isnull=True) | Q(project__status=approved),
            Q(article__isnull=True)
            | (Q(article__project__status=approved) & globally_visible_q("article__")),
            Q(discussion__isnull=True) | Q(discussion__project__status=approved),
        )

    def with_sources(self) -> "FeedEventQuerySet":
        """Pull every entity a row can render from, in one query.

        A feed page mixes kinds, so there is no single shape to select; joining
        all three is still one round trip and cheaper than resolving per row.
        """
        # Local import: `services` builds the whole handler registry on import,
        # and that registry reaches back into this module.
        from services.images.django_impl.query import gallery_prefetch  # noqa: PLC0415

        return self.select_related(
            "project",
            "project__category",
            "article",
            "article__channel",
            "article__project",
            "article__listing_image",
            "discussion",
            "discussion__project",
        ).prefetch_related(
            # Project rows show the project's icon. gallery_prefetch rather than
            # a plain prefetch: it filters to the project's own uploaded gallery,
            # without which the fallback chain can land on an article figure or
            # a row whose upload never completed.
            gallery_prefetch("project__images"),
            "project__images__variants",
        )


class FeedEvent(models.Model):
    """One thing that happened, appended and never moved.

    The stream is append-only and ordered by ``occurred_at``: an entry's
    position is fixed once written, which is what lets the read path paginate on
    a stable cursor.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=32, choices=FeedEventKind.choices)
    occurred_at = models.DateTimeField()

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feed_events",
    )
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feed_events",
    )
    discussion = models.ForeignKey(
        "discussions.Discussion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feed_events",
    )

    # Set when an admin withdraws an entry.
    retired_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = FeedEventQuerySet.as_manager()

    class Meta:
        db_table = "feed_events"
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["-occurred_at", "-created_at"],
                name="feed_events_occurred_idx",
            ),
            # The read path always filters to renderable rows; a partial index
            # keeps retired history out of the hot path.
            models.Index(
                fields=["-occurred_at"],
                condition=Q(retired_at__isnull=True),
                name="feed_events_live_idx",
            ),
        ]
        constraints = [
            # Idempotency lives in the schema, not only in the appender: the
            # backfill re-running, or a signal firing twice, cannot duplicate a
            # row. Each event has exactly one subject.
            #
            # A project gets one entry for the fact it appeared — announced
            # either as a new project or as a tipoff, never both.
            models.UniqueConstraint(
                fields=("project",),
                condition=Q(project__isnull=False),
                name="feed_events_project_uniq",
            ),
            models.UniqueConstraint(
                fields=("article",),
                condition=Q(article__isnull=False),
                name="feed_events_article_uniq",
            ),
            models.UniqueConstraint(
                fields=("discussion",),
                condition=Q(discussion__isnull=False),
                name="feed_events_discussion_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(project__isnull=False)
                    | Q(article__isnull=False)
                    | Q(discussion__isnull=False)
                ),
                name="feed_events_has_subject",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_kind_display()}: {self.subject} @ {self.occurred_at:%Y-%m-%d}"
        )

    @property
    def subject(self) -> str:
        """What the entry is about, for admin labels.

        Kind and date alone do not identify a row — a week with two approvals
        would list two identical "Project published @ 2026-08-14" entries.
        """
        for candidate in (self.article, self.project, self.discussion):
            if candidate is not None:
                return str(candidate)
        return "—"
