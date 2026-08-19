from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.articles.models import ArticleState
from apps.emails.models import SentEmail
from apps.feed.models import FeedEvent, FeedEventKind
from apps.notifications.models import Notification
from apps.projects.models import ProjectStatus
from tests.factories import ArticleFactory, CompetitionFactory, ProjectFactory


def run_backfill() -> None:
    call_command("backfill_feed")


def dry_run_backfill() -> str:
    output = StringIO()
    call_command("backfill_feed", "--dry-run", stdout=output)
    return output.getvalue()


def wipe_stream() -> None:
    """Mimic history that predates the stream — the rows exist, the events don't."""
    FeedEvent.objects.all().delete()


def approved_project(**kwargs):
    return ProjectFactory(
        status=ProjectStatus.APPROVED,
        approved_at=kwargs.pop("approved_at", timezone.now()),
        **kwargs,
    )


@pytest.mark.django_db
class TestBackfill:
    def test_seeds_projects_at_their_original_times(self):
        approved_at = timezone.now() - timedelta(days=200)
        project = approved_project(approved_at=approved_at)
        wipe_stream()

        run_backfill()

        assert FeedEvent.objects.get(project=project).occurred_at == approved_at

    def test_reaches_back_with_no_cut_off(self):
        ancient = approved_project(approved_at=timezone.now() - timedelta(days=3000))
        wipe_stream()

        run_backfill()

        assert FeedEvent.objects.filter(project=ancient).exists()

    def test_seeds_competition_milestones(self):
        competition = CompetitionFactory(
            start_date=date(2025, 1, 1), winner=ProjectFactory()
        )
        wipe_stream()

        run_backfill()

        kinds = set(
            FeedEvent.objects.filter(competition=competition).values_list(
                "kind", flat=True
            )
        )
        assert FeedEventKind.COMPETITION_OPENED in kinds
        assert FeedEventKind.COMPETITION_WINNER in kinds

    def test_seeds_the_closing_of_a_competition_with_no_winner(self):
        competition = CompetitionFactory(
            start_date=date(2025, 1, 1), submission_deadline=date(2025, 1, 31)
        )
        wipe_stream()

        run_backfill()

        closed = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_SUBMISSIONS_CLOSED
        )
        assert closed.occurred_at.date() == date(2025, 1, 31)

    def test_skips_unapproved_projects(self):
        pending = ProjectFactory(status=ProjectStatus.PENDING)
        wipe_stream()

        run_backfill()

        assert not FeedEvent.objects.filter(project=pending).exists()

    def test_does_not_backfill_articles(self):
        project = approved_project()
        article = ArticleFactory(project=project, state=ArticleState.PUBLISHED)
        wipe_stream()

        run_backfill()

        assert not FeedEvent.objects.filter(article=article).exists()


@pytest.mark.django_db
class TestBackfillIdempotency:
    def test_running_twice_changes_nothing(self):
        approved_project()
        CompetitionFactory(start_date=date(2025, 1, 1), winner=ProjectFactory())
        wipe_stream()
        run_backfill()
        after_first = set(FeedEvent.objects.values_list("id", flat=True))

        run_backfill()

        assert set(FeedEvent.objects.values_list("id", flat=True)) == after_first

    def test_second_run_appends_only_what_is_missing(self):
        approved_project()
        wipe_stream()
        run_backfill()
        after_first = set(FeedEvent.objects.values_list("id", flat=True))
        later = approved_project()
        FeedEvent.objects.filter(project=later).delete()

        run_backfill()

        added = set(FeedEvent.objects.values_list("id", flat=True)) - after_first
        assert len(added) == 1
        assert FeedEvent.objects.get(id=next(iter(added))).project_id == later.id


@pytest.mark.django_db
class TestBackfillIsSilent:
    def test_fires_no_notifications_and_no_email(self):
        approved_project()
        CompetitionFactory(start_date=date(2025, 1, 1), winner=ProjectFactory())
        wipe_stream()
        notifications_before = Notification.objects.count()
        emails_before = SentEmail.objects.count()

        run_backfill()

        assert Notification.objects.count() == notifications_before
        assert SentEmail.objects.count() == emails_before


@pytest.mark.django_db
class TestBackfillDryRun:
    def test_writes_nothing(self):
        approved_project()
        wipe_stream()

        dry_run_backfill()

        assert FeedEvent.objects.count() == 0

    def test_reports_what_a_real_run_would_append(self):
        approved_project()
        # Opened and won — two milestones, not three: announcing a winner is
        # what closed it, so there is no separate closure to report.
        CompetitionFactory(start_date=date(2025, 1, 1), winner=ProjectFactory())
        wipe_stream()

        report = dry_run_backfill()

        assert "would append 1 project entries" in report
        assert "2 competition entries" in report

    def test_reports_nothing_once_the_stream_is_already_covered(self):
        approved_project()
        CompetitionFactory(start_date=date(2025, 1, 1), winner=ProjectFactory())
        run_backfill()

        report = dry_run_backfill()

        assert "would append 0 project entries" in report
        assert "0 competition entries" in report
