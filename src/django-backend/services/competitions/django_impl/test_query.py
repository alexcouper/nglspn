from uuid import uuid4

import pytest

from apps.projects.models import CompetitionStatus, ProjectStatus
from services.competitions.django_impl import DjangoCompetitionQuery
from services.competitions.exceptions import CompetitionNotFoundError
from tests.factories import CompetitionFactory, ProjectFactory

query = DjangoCompetitionQuery()


@pytest.mark.django_db
class TestListAll:
    def test_returns_all_competitions_with_counts(self):
        competition = CompetitionFactory()
        project = ProjectFactory()
        competition.projects.add(project)

        result = query.list_all()

        assert len(result) == 1
        assert result[0].competition.id == competition.id
        assert result[0].project_count == 1

    def test_returns_empty_list_when_none_exist(self):
        result = query.list_all()

        assert result == []


@pytest.mark.django_db
class TestListWithProjects:
    def test_returns_competitions_with_project_items(self):
        competition = CompetitionFactory()
        project = ProjectFactory()
        competition.projects.add(project)

        result = query.list_with_projects()

        assert len(result) == 1
        assert result[0].competition.id == competition.id
        assert len(result[0].project_items) >= 0


@pytest.mark.django_db
class TestGetByIdOrSlug:
    def test_returns_competition_by_id(self):
        competition = CompetitionFactory()

        result = query.get_by_id_or_slug(str(competition.id))

        assert result.competition.id == competition.id

    def test_returns_competition_by_slug(self):
        competition = CompetitionFactory(slug="test-comp")

        result = query.get_by_id_or_slug("test-comp")

        assert result.competition.id == competition.id

    def test_raises_for_nonexistent_id(self):
        with pytest.raises(CompetitionNotFoundError):
            query.get_by_id_or_slug(str(uuid4()))

    def test_raises_for_nonexistent_slug(self):
        with pytest.raises(CompetitionNotFoundError):
            query.get_by_id_or_slug("nonexistent-slug")


@pytest.mark.django_db
class TestListHighlights:
    def test_returns_active_competitions(self):
        CompetitionFactory(status=CompetitionStatus.ACCEPTING_APPLICATIONS)
        CompetitionFactory(status=CompetitionStatus.VOTING)
        CompetitionFactory(status=CompetitionStatus.CLOSED)

        result = query.list_highlights()

        active_names = {h.competition.status for h in result}
        assert (
            CompetitionStatus.ACCEPTING_APPLICATIONS in active_names
            or CompetitionStatus.VOTING in active_names
        )

    def test_includes_recent_closed(self):
        CompetitionFactory(status=CompetitionStatus.CLOSED)

        result = query.list_highlights()

        assert len(result) >= 1


@pytest.mark.django_db
class TestCountPendingProjects:
    def test_counts_pending_projects(self):
        ProjectFactory()
        ProjectFactory()

        count = query.count_pending_projects()

        assert count >= 2

    def test_excludes_non_pending(self):
        ProjectFactory(status=ProjectStatus.APPROVED)

        count = query.count_pending_projects()

        assert count == 0
