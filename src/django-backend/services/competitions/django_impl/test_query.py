from uuid import uuid4

import pytest

from apps.projects.models import CompetitionStatus, ProjectStatus
from services.competitions.django_impl import DjangoCompetitionQuery
from services.competitions.exceptions import CompetitionNotFoundError
from tests.factories import CompetitionFactory, ProjectFactory

query = DjangoCompetitionQuery()


@pytest.mark.django_db
class TestListAll:
    def test_returns_all_competitions(self):
        CompetitionFactory()
        CompetitionFactory()

        result = list(query.list_all())

        assert len(result) == 2


@pytest.mark.django_db
class TestGetByIdOrSlug:
    def test_gets_by_uuid(self):
        competition = CompetitionFactory()

        result = query.get_by_id_or_slug(str(competition.id))

        assert result.id == competition.id

    def test_gets_by_slug(self):
        competition = CompetitionFactory(name="My Comp")

        result = query.get_by_id_or_slug(competition.slug)

        assert result.id == competition.id

    def test_raises_when_not_found(self):
        with pytest.raises(CompetitionNotFoundError):
            query.get_by_id_or_slug(str(uuid4()))

    def test_raises_when_slug_not_found(self):
        with pytest.raises(CompetitionNotFoundError):
            query.get_by_id_or_slug("nonexistent-slug")


@pytest.mark.django_db
class TestListHighlights:
    def test_includes_active_competitions(self):
        CompetitionFactory(status=CompetitionStatus.ACCEPTING_APPLICATIONS)
        CompetitionFactory(status=CompetitionStatus.VOTING)
        CompetitionFactory(status=CompetitionStatus.PENDING)

        result = query.list_highlights()

        statuses = [h.competition.status for h in result]
        assert CompetitionStatus.ACCEPTING_APPLICATIONS in statuses
        assert CompetitionStatus.VOTING in statuses
        assert CompetitionStatus.PENDING not in statuses

    def test_includes_one_recent_closed(self):
        winner = ProjectFactory()
        CompetitionFactory(status=CompetitionStatus.CLOSED, winner=winner)
        CompetitionFactory(status=CompetitionStatus.CLOSED, winner=winner)

        result = query.list_highlights()

        closed = [h for h in result if h.competition.status == CompetitionStatus.CLOSED]
        assert len(closed) == 1

    def test_annotates_project_count(self):
        comp = CompetitionFactory(status=CompetitionStatus.VOTING)
        comp.projects.add(ProjectFactory(), ProjectFactory())

        result = query.list_highlights()

        assert result[0].project_count == 2


@pytest.mark.django_db
class TestCountPendingProjects:
    def test_counts_pending_only(self):
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.APPROVED)

        assert query.count_pending_projects() == 2
