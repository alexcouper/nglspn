from contextlib import contextmanager
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.articles.models import ArticleState
from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services import HANDLERS
from tests.factories import (
    ArticleFactory,
    CompetitionFactory,
    DiscussionFactory,
    ProjectFactory,
)


def days_from_now(days: int) -> date:
    return (timezone.now() + timedelta(days=days)).date()


def renderable_kinds_for(competition) -> set[str]:
    return set(
        FeedEvent.objects.renderable()
        .filter(competition=competition)
        .values_list("kind", flat=True)
    )


@contextmanager
def clock_at(moment: datetime):
    """Move the wall clock forward.

    The only way to reveal a scheduled entry: it surfaces by time alone, which
    is the whole point — there is no save to make and nothing else to trigger.
    """
    with patch("django.utils.timezone.now", return_value=moment):
        yield


def kinds_for(**subject) -> list[str]:
    return list(FeedEvent.objects.filter(**subject).values_list("kind", flat=True))


def approved_project(**kwargs):
    return ProjectFactory(
        status=ProjectStatus.APPROVED,
        approved_at=kwargs.pop("approved_at", timezone.now()),
        **kwargs,
    )


def published_article(project=None, *, published_at=None, **kwargs):
    article = ArticleFactory(
        project=project or approved_project(),
        state=ArticleState.DRAFT,
        **kwargs,
    )
    return HANDLERS.articles.publish(article.id, published_at=published_at)


@pytest.mark.django_db
class TestArticleAppends:
    def test_publishing_appends_one_event_at_published_at(self):
        article = published_article()

        events = FeedEvent.objects.filter(article=article)
        assert [e.kind for e in events] == [FeedEventKind.ARTICLE_PUBLISHED]
        assert events[0].occurred_at == article.published_at

    def test_backdated_publish_lands_at_the_backdated_time(self):
        backdated = timezone.now() - timedelta(days=40)

        article = published_article(published_at=backdated)

        event = FeedEvent.objects.get(article=article)
        assert event.occurred_at == backdated

    def test_editing_a_published_article_appends_nothing(self):
        article = published_article()

        HANDLERS.articles.update_article(article.id, title="Edited afterwards")

        assert FeedEvent.objects.filter(article=article).count() == 1

    def test_draft_article_has_no_event(self):
        ArticleFactory(project=approved_project(), state=ArticleState.DRAFT)

        assert (
            FeedEvent.objects.filter(kind=FeedEventKind.ARTICLE_PUBLISHED).count() == 0
        )


@pytest.mark.django_db
class TestProjectAppends:
    def test_approved_project_appends_a_new_project_event(self):
        project = approved_project()

        assert kinds_for(project=project) == [FeedEventKind.PROJECT_PUBLISHED]

    def test_approved_tipoff_appends_a_tipoff_event_instead(self):
        project = approved_project(is_community_tipoff=True)

        assert kinds_for(project=project) == [FeedEventKind.PROJECT_TIPOFF]

    def test_unapproved_project_has_no_event(self):
        project = ProjectFactory(status=ProjectStatus.PENDING)

        assert kinds_for(project=project) == []

    def test_event_time_matches_approval_not_submission(self):
        approved_at = timezone.now() - timedelta(days=5)

        project = approved_project(
            approved_at=approved_at,
            published_at=timezone.now() - timedelta(days=9),
        )

        assert FeedEvent.objects.get(project=project).occurred_at == approved_at

    def test_re_saving_an_approved_project_appends_nothing_further(self):
        project = approved_project()

        project.title = "Renamed"
        project.save()

        assert FeedEvent.objects.filter(project=project).count() == 1


@pytest.mark.django_db
class TestCompetitionAppends:
    def test_competition_gets_an_opened_event_at_its_start_date(self):
        competition = CompetitionFactory(start_date=date(2025, 3, 1))

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_OPENED
        )
        assert event.occurred_at.date() == date(2025, 3, 1)

    def test_announcing_a_winner_appends_a_winner_event(self):
        competition = CompetitionFactory()

        competition.winner = ProjectFactory()
        competition.save()

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_WINNER
        )
        assert event.occurred_at == competition.winner_announced_at

    def test_winner_event_is_not_duplicated_when_the_winner_changes(self):
        competition = CompetitionFactory(winner=ProjectFactory())

        competition.winner = ProjectFactory()
        competition.save()

        assert (
            FeedEvent.objects.filter(
                competition=competition, kind=FeedEventKind.COMPETITION_WINNER
            ).count()
            == 1
        )

    def test_competition_without_a_winner_has_no_winner_event(self):
        competition = CompetitionFactory()

        assert (
            FeedEvent.objects.filter(
                competition=competition, kind=FeedEventKind.COMPETITION_WINNER
            ).count()
            == 0
        )


@pytest.mark.django_db
class TestCompetitionMilestonesAreDateDriven:
    """Opening and closing are dates, and nothing saves a competition on the day
    one arrives. Both entries are appended as soon as the date is known and held
    out of the feed until it comes round.
    """

    def _opening_in(self, days: int, **kwargs):
        return CompetitionFactory(
            start_date=days_from_now(days),
            submission_deadline=days_from_now(days + 30),
            voting_end_date=days_from_now(days + 45),
            **kwargs,
        )

    def test_a_competition_opening_later_is_scheduled_not_served(self):
        competition = self._opening_in(14)

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_OPENED
        )
        assert event.occurred_at.date() == days_from_now(14)
        assert renderable_kinds_for(competition) == set()

    def test_a_scheduled_opening_surfaces_on_the_day_without_a_further_save(self):
        opens_in = 14
        competition = self._opening_in(opens_in)

        with clock_at(timezone.now() + timedelta(days=opens_in + 1)):
            assert FeedEventKind.COMPETITION_OPENED in renderable_kinds_for(competition)

    def test_moving_the_start_date_moves_an_entry_nobody_has_seen(self):
        competition = self._opening_in(14)

        competition.start_date = days_from_now(21)
        competition.save()

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_OPENED
        )
        assert event.occurred_at.date() == days_from_now(21)

    def test_moving_the_start_date_leaves_an_entry_already_in_the_feed_alone(self):
        competition = CompetitionFactory(start_date=date(2025, 3, 1))

        competition.start_date = date(2025, 4, 1)
        competition.save()

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_OPENED
        )
        assert event.occurred_at.date() == date(2025, 3, 1)

    def test_submissions_closing_is_dated_to_the_submission_deadline(self):
        """Not `voting_end_date`: the beat the feed carries is entries closing
        and voting opening, which is the one a reader can act on.
        """
        competition = CompetitionFactory(
            submission_deadline=date(2025, 1, 31), voting_end_date=date(2025, 2, 15)
        )

        event = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_SUBMISSIONS_CLOSED
        )
        assert event.occurred_at.date() == date(2025, 1, 31)

    def test_voting_ending_appends_nothing_of_its_own(self):
        competition = CompetitionFactory(
            submission_deadline=date(2025, 1, 31), voting_end_date=date(2025, 2, 15)
        )

        occurred = {
            event.occurred_at.date()
            for event in FeedEvent.objects.filter(competition=competition)
        }
        assert date(2025, 2, 15) not in occurred

    def test_a_competition_still_taking_entries_has_no_closing_entry(self):
        competition = self._opening_in(-1)

        assert renderable_kinds_for(competition) == {FeedEventKind.COMPETITION_OPENED}

    def test_the_deadline_passing_closes_entries_with_nobody_touching_the_row(self):
        """The case a status check could never catch: the deadline runs out and
        the competition is not saved again until someone picks a winner.
        """
        competition = self._opening_in(-1)

        # Past the submission deadline, still short of the voting end date.
        with clock_at(timezone.now() + timedelta(days=31)):
            assert renderable_kinds_for(competition) == {
                FeedEventKind.COMPETITION_OPENED,
                FeedEventKind.COMPETITION_SUBMISSIONS_CLOSED,
            }


@pytest.mark.django_db
class TestACompetitionsThreeBeats:
    """Opened, entries closed, winner announced — one row each, in order."""

    def test_a_decided_competition_carries_all_three(self):
        competition = CompetitionFactory()

        competition.winner = ProjectFactory()
        competition.save()

        assert set(kinds_for(competition=competition)) == {
            FeedEventKind.COMPETITION_OPENED,
            FeedEventKind.COMPETITION_SUBMISSIONS_CLOSED,
            FeedEventKind.COMPETITION_WINNER,
        }

    def test_the_closing_entry_stays_on_the_deadline_not_the_announcement(self):
        """The bug this replaced: the entry was written when the winner was
        assigned and backdated to compensate, landing behind the page boundary
        a reader had already passed.
        """
        competition = CompetitionFactory(submission_deadline=date(2025, 1, 31))

        competition.winner = ProjectFactory()
        competition.save()

        closed = FeedEvent.objects.get(
            competition=competition, kind=FeedEventKind.COMPETITION_SUBMISSIONS_CLOSED
        )
        assert closed.occurred_at.date() == date(2025, 1, 31)

    def test_a_winner_picked_before_entries_closed_cancels_that_beat(self):
        """A decided competition does not go on to announce that its entries
        have closed a week later.
        """
        competition = CompetitionFactory(
            start_date=days_from_now(-1),
            submission_deadline=days_from_now(7),
            voting_end_date=days_from_now(14),
        )
        assert FeedEventKind.COMPETITION_SUBMISSIONS_CLOSED in kinds_for(
            competition=competition
        )

        competition.winner = ProjectFactory()
        competition.save()

        assert set(kinds_for(competition=competition)) == {
            FeedEventKind.COMPETITION_OPENED,
            FeedEventKind.COMPETITION_WINNER,
        }


@pytest.mark.django_db
class TestSourcesThatAppendNothing:
    def test_creating_a_discussion_appends_nothing(self):
        DiscussionFactory(project=approved_project())

        assert (
            FeedEvent.objects.filter(kind=FeedEventKind.DISCUSSION_PROMOTED).count()
            == 0
        )

    def test_replying_to_a_discussion_appends_nothing(self):
        thread = DiscussionFactory(project=approved_project())

        DiscussionFactory(project=thread.project, parent=thread)

        assert (
            FeedEvent.objects.filter(kind=FeedEventKind.DISCUSSION_PROMOTED).count()
            == 0
        )

    def test_deleting_a_published_article_removes_its_entry(self):
        article = published_article()

        HANDLERS.articles.delete_article(article.id)

        assert FeedEvent.objects.filter(article_id=article.id).count() == 0

    def test_promoting_a_discussion_is_what_appends(self):
        discussion = DiscussionFactory(project=approved_project())

        HANDLERS.feed.promote_discussion(discussion)

        assert kinds_for(discussion=discussion) == [FeedEventKind.DISCUSSION_PROMOTED]
