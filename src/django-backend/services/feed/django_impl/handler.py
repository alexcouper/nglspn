from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import CompetitionStatus, ProjectStatus
from services.feed.exceptions import FeedEventNotFoundError
from services.feed.handler_interface import FeedHandlerInterface

if TYPE_CHECKING:
    from uuid import UUID

    from apps.articles.models import Article
    from apps.discussions.models import Discussion
    from apps.projects.models import Competition, Project


def as_datetime(
    value: datetime.date | datetime.datetime | str | None,
) -> datetime.datetime:
    """Competition milestones are dates; the stream is ordered by datetimes.

    Midnight is imprecise for history and exact for anything from here on,
    which is the right way round.

    Strings are accepted because a field assigned a literal has not been coerced
    to a date by the time post_save fires — the instance still holds what the
    caller set, so appending straight from it would see `"2026-01-15"`.
    """
    if value is None:
        return timezone.now()
    if isinstance(value, str):
        value = parse_datetime(value) or parse_date(value)
        if value is None:
            return timezone.now()
    if isinstance(value, datetime.datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)
    naive = datetime.datetime.combine(value, datetime.time.min)
    return timezone.make_aware(naive, timezone.get_default_timezone())


class DjangoFeedHandler(FeedHandlerInterface):
    def append_article_published(self, article: Article) -> FeedEvent | None:
        return self._append(
            FeedEventKind.ARTICLE_PUBLISHED,
            occurred_at=as_datetime(article.published_at),
            article=article,
        )

    def append_project_published(self, project: Project) -> FeedEvent | None:
        """A project enters the feed when it becomes visible, not when submitted.

        `published_at` marks submission for review; `approved_at` is when the
        site actually shows it. Discover already orders arrivals by
        `Coalesce(approved_at, created_at)` and the feed matches it, so the two
        surfaces agree about when something turned up.
        """
        if project.status != ProjectStatus.APPROVED:
            return None
        kind = (
            FeedEventKind.PROJECT_TIPOFF
            if project.is_community_tipoff
            else FeedEventKind.PROJECT_PUBLISHED
        )
        return self._append(
            kind,
            occurred_at=as_datetime(project.approved_at or project.created_at),
            project=project,
        )

    def append_project_tipoff(self, project: Project) -> FeedEvent | None:
        if project.status != ProjectStatus.APPROVED:
            return None
        return self._append(
            FeedEventKind.PROJECT_TIPOFF,
            occurred_at=as_datetime(project.approved_at or project.created_at),
            project=project,
        )

    def append_competition_opened(self, competition: Competition) -> FeedEvent | None:
        # A competition can be created weeks before it opens. Appending then
        # would put a future-dated row at the top of the feed, so the event
        # waits until the date has actually arrived.
        opened_at = as_datetime(competition.start_date)
        if opened_at > timezone.now():
            return None
        return self._append(
            FeedEventKind.COMPETITION_OPENED,
            occurred_at=opened_at,
            competition=competition,
        )

    def append_competition_closed(self, competition: Competition) -> FeedEvent | None:
        if competition.status != CompetitionStatus.CLOSED:
            return None
        deadline = competition.voting_end_date or competition.submission_deadline
        # Setting a winner closes a competition early, so the deadline can still
        # be ahead of us; the feed records when it actually closed.
        return self._append(
            FeedEventKind.COMPETITION_CLOSED,
            occurred_at=min(as_datetime(deadline), timezone.now()),
            competition=competition,
        )

    def append_competition_winner(self, competition: Competition) -> FeedEvent | None:
        if competition.winner_id is None:
            return None
        return self._append(
            FeedEventKind.COMPETITION_WINNER,
            occurred_at=as_datetime(competition.winner_announced_at),
            competition=competition,
        )

    def promote_discussion(
        self,
        discussion: Discussion,
        *,
        occurred_at: datetime.datetime | None = None,
    ) -> FeedEvent | None:
        existing = FeedEvent.objects.filter(discussion=discussion).first()
        if existing is not None:
            # Promoting a previously retired thread brings it back rather than
            # colliding with the row that is already there.
            if existing.retired_at is not None:
                existing.retired_at = None
                existing.save(update_fields=["retired_at"])
            return existing
        return self._append(
            FeedEventKind.DISCUSSION_PROMOTED,
            occurred_at=occurred_at or timezone.now(),
            discussion=discussion,
        )

    def retire(self, event_id: UUID) -> FeedEvent:
        event = self._get(event_id)
        if event.retired_at is None:
            event.retired_at = timezone.now()
            event.save(update_fields=["retired_at"])
        return event

    def unretire(self, event_id: UUID) -> FeedEvent:
        event = self._get(event_id)
        if event.retired_at is not None:
            event.retired_at = None
            event.save(update_fields=["retired_at"])
        return event

    def set_pinned(self, event_id: UUID, *, pinned: bool) -> FeedEvent:
        event = self._get(event_id)
        with transaction.atomic():
            if pinned:
                # One lead at a time — pinning a second entry replaces the first
                # rather than leaving the choice to ordering.
                FeedEvent.objects.filter(is_pinned=True).exclude(pk=event.pk).update(
                    is_pinned=False
                )
            if event.is_pinned != pinned:
                event.is_pinned = pinned
                event.save(update_fields=["is_pinned"])
        return event

    def link_article_to_event(
        self,
        article: Article,
        event_id: UUID | None,
    ) -> FeedEvent | None:
        """Point the event this article writes up at the article's own entry.

        Two-way, because a supersession only holds while the write-up is being
        served. An article awaiting review or demoted cannot stand in for what it
        replaced — the bare event would be hidden as superseded and the article's
        entry hidden as invisible, so the feed would show neither. Called from the
        post_save signal, so approving or demoting the article re-runs this and
        the link follows.
        """
        with transaction.atomic():
            superseding = FeedEvent.objects.filter(article=article).first()
            if superseding is None:
                return None

            if not article.is_globally_visible:
                # Hand back whatever this article had taken the place of. It can
                # take it again on approval: the guard below only skips a target
                # that is *still* superseded.
                FeedEvent.objects.filter(superseded_by=superseding).update(
                    superseded_by=None
                )
                return None

            if event_id is None:
                return None

            target = (
                FeedEvent.objects.select_for_update()
                .filter(pk=event_id, superseded_by__isnull=True)
                .exclude(pk=superseding.pk)
                .first()
            )
            # Already superseded once, or absent: the article stands on its own.
            # Superseding is one-shot by design.
            if target is None:
                return None

            target.superseded_by = superseding
            target.save(update_fields=["superseded_by"])
            return target

    def _append(
        self,
        kind: str,
        *,
        occurred_at: datetime.datetime,
        **subject,
    ) -> FeedEvent | None:
        """Append, or return the row that is already there.

        The unique constraints are the real guard; catching IntegrityError
        rather than checking first keeps concurrent appends safe.
        """
        lookup = self._idempotency_lookup(kind, subject)
        existing = FeedEvent.objects.filter(**lookup).first()
        if existing is not None:
            return existing
        try:
            with transaction.atomic():
                return FeedEvent.objects.create(
                    kind=kind, occurred_at=occurred_at, **subject
                )
        except IntegrityError:
            return FeedEvent.objects.filter(**lookup).first()

    @staticmethod
    def _idempotency_lookup(kind: str, subject: dict) -> dict:
        # Competitions carry several milestones, so kind is part of their
        # identity. Everything else gets one entry per subject.
        if "competition" in subject:
            return {"kind": kind, **subject}
        return dict(subject)

    @staticmethod
    def _get(event_id: UUID) -> FeedEvent:
        event = FeedEvent.objects.filter(pk=event_id).first()
        if event is None:
            raise FeedEventNotFoundError(event_id)
        return event
