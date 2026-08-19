import pytest
from django.utils import timezone

from apps.projects.models import Competition
from tests.factories import CompetitionFactory, ProjectFactory


def announce_winner(competition: Competition, project) -> Competition:
    competition.winner = project
    competition.save()
    competition.refresh_from_db()
    return competition


def assert_announced_between(competition: Competition, start, end) -> None:
    assert competition.winner_announced_at is not None
    assert start <= competition.winner_announced_at <= end


@pytest.mark.django_db
class TestWinnerAnnouncedAt:
    def test_competition_without_winner_has_no_announced_time(self):
        competition = CompetitionFactory()
        assert competition.winner_announced_at is None

    def test_first_winner_assignment_records_the_time(self):
        competition = CompetitionFactory()
        before = timezone.now()

        announce_winner(competition, ProjectFactory())

        assert_announced_between(competition, before, timezone.now())

    def test_reassigning_the_winner_does_not_move_the_time(self):
        competition = announce_winner(CompetitionFactory(), ProjectFactory())
        originally_announced = competition.winner_announced_at

        announce_winner(competition, ProjectFactory())

        assert competition.winner_announced_at == originally_announced

    def test_saving_an_unrelated_field_does_not_move_the_time(self):
        competition = announce_winner(CompetitionFactory(), ProjectFactory())
        originally_announced = competition.winner_announced_at

        competition.quote = "Edited well after the fact"
        competition.save()
        competition.refresh_from_db()

        assert competition.winner_announced_at == originally_announced

    def test_clearing_the_winner_clears_the_time(self):
        competition = announce_winner(CompetitionFactory(), ProjectFactory())

        competition.winner = None
        competition.save()
        competition.refresh_from_db()

        assert competition.winner_announced_at is None

    def test_reassigning_after_clearing_records_a_new_time(self):
        competition = announce_winner(CompetitionFactory(), ProjectFactory())
        first_announcement = competition.winner_announced_at
        competition.winner = None
        competition.save()

        before = timezone.now()
        announce_winner(competition, ProjectFactory())

        assert competition.winner_announced_at > first_announcement
        assert_announced_between(competition, before, timezone.now())
