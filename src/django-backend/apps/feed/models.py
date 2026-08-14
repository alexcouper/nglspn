import uuid

from django.db import models
from django.db.models import Q


class FeedEventKind(models.TextChoices):
    ARTICLE_PUBLISHED = "article_published", "Article published"
    PROJECT_PUBLISHED = "project_published", "Project published"
    PROJECT_TIPOFF = "project_tipoff", "Community tipoff"
    COMPETITION_OPENED = "competition_opened", "Competition opened"
    COMPETITION_CLOSED = "competition_closed", "Competition closed"
    COMPETITION_WINNER = "competition_winner", "Competition winner announced"
    DISCUSSION_PROMOTED = "discussion_promoted", "Discussion promoted"


class FeedEventQuerySet(models.QuerySet["FeedEvent"]):
    def renderable(self) -> "FeedEventQuerySet":
        return self.filter(
            superseded_by__isnull=True,
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

        Competition entries have no such state and are left alone.
        """
        # Local imports: those apps own their own visibility vocabulary, and both
        # FKs are declared lazily, so this is the only place the modules meet.
        from apps.articles.models import globally_visible_q  # noqa: PLC0415
        from apps.projects.models import ProjectStatus  # noqa: PLC0415

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
        all four is still one round trip and cheaper than resolving per row.
        """
        # Local import: `services` builds the whole handler registry on import,
        # and that registry reaches back into this module.
        from services.images.django_impl.query import gallery_prefetch  # noqa: PLC0415

        # The superseded side goes through the same visibility rule as the rows
        # themselves. Without it a write-up keeps publishing the title, tagline
        # and icon of the project whose entry it replaced, long after that
        # project was rejected or iced — `renderable()` only reaches the row's
        # own subject, not the one hanging off `supersedes`.
        superseded = models.Prefetch(
            "supersedes",
            queryset=FeedEvent.objects.visible_subject(),
        )

        return self.select_related(
            "project",
            "project__category",
            "competition",
            "competition__winner",
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
            # An article-led row renders the flag of the event it took the place
            # of, so the reverse side is needed too — prefetched rather than
            # walked per row.
            superseded,
            "supersedes__competition",
            "supersedes__competition__winner",
            "supersedes__project",
            "supersedes__project__category",
            # The superseded project is serialised by the same `_project_ref`
            # as a top-level one, icon and all, so it needs the same gallery
            # prefetch — otherwise every write-up of a project costs two extra
            # queries and the page's cost stops being flat in the row count.
            gallery_prefetch("supersedes__project__images"),
            "supersedes__project__images__variants",
        )


class FeedEvent(models.Model):
    """One thing that happened, appended and never moved.

    The stream is append-only and ordered by ``occurred_at``: an entry's
    position is fixed once written, which is what lets the read path paginate on
    a stable cursor. A later write-up does not re-date its event — it appends
    its own and points the older one at it via ``superseded_by``.
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
    competition = models.ForeignKey(
        "projects.Competition",
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

    # Points at the event that took this one's place. SET_NULL rather than
    # CASCADE on purpose: deleting the superseding article deletes its event,
    # and this row must come back into the feed rather than vanish with it.
    superseded_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
    )
    # Set when an admin withdraws an entry — distinct from being superseded,
    # which is the system's own doing.
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
            # keeps retired and superseded history out of the hot path.
            models.Index(
                fields=["-occurred_at"],
                condition=Q(superseded_by__isnull=True, retired_at__isnull=True),
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
            # A competition legitimately produces several: opened, closed, won.
            models.UniqueConstraint(
                fields=("kind", "competition"),
                condition=Q(competition__isnull=False),
                name="feed_events_kind_competition_uniq",
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
                    | Q(competition__isnull=False)
                    | Q(discussion__isnull=False)
                ),
                name="feed_events_has_subject",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} @ {self.occurred_at:%Y-%m-%d}"

    @property
    def is_renderable(self) -> bool:
        return self.superseded_by_id is None and self.retired_at is None
