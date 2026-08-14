from datetime import date
from importlib import import_module

import pytest
from django.apps import apps as django_apps

from apps.projects.models import Competition
from tests.factories import CompetitionFactory, ProjectFactory

migration_module = import_module(
    "apps.projects.migrations.0048_backfill_competition_winner_announced_at"
)


def clear_announced_time(competition: Competition) -> Competition:
    """Undo the model's own stamping, to mimic a row predating the field."""
    Competition.objects.filter(pk=competition.pk).update(winner_announced_at=None)
    competition.refresh_from_db()
    return competition


def won_competition(**kwargs) -> Competition:
    competition = CompetitionFactory(winner=ProjectFactory(), **kwargs)
    return clear_announced_time(competition)


@pytest.mark.django_db
class TestWinnerAnnouncedAtBackfill:
    def _run_forward(self):
        migration_module.backfill_winner_announced_at(django_apps, schema_editor=None)

    def test_uses_voting_end_date_when_present(self):
        competition = won_competition(
            submission_deadline=date(2025, 1, 31),
            voting_end_date=date(2025, 2, 15),
        )

        self._run_forward()

        competition.refresh_from_db()
        assert competition.winner_announced_at.date() == date(2025, 2, 15)

    def test_falls_back_to_submission_deadline(self):
        competition = won_competition(
            submission_deadline=date(2025, 1, 31),
            voting_end_date=None,
        )

        self._run_forward()

        competition.refresh_from_db()
        assert competition.winner_announced_at.date() == date(2025, 1, 31)

    def test_leaves_competitions_without_a_winner_alone(self):
        competition = CompetitionFactory(winner=None)

        self._run_forward()

        competition.refresh_from_db()
        assert competition.winner_announced_at is None

    def test_does_not_overwrite_an_existing_announcement_time(self):
        competition = CompetitionFactory(winner=ProjectFactory())
        already_announced = competition.winner_announced_at

        self._run_forward()

        competition.refresh_from_db()
        assert competition.winner_announced_at == already_announced
