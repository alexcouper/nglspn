from uuid import uuid4

import pytest

from apps.projects.models import ProjectStatus, ReviewStatus
from services.review.django_impl import DjangoReviewHandler, DjangoReviewQuery
from services.review.exceptions import (
    InvalidProjectIdsError,
    ReviewAlreadyCompletedError,
    ReviewNotFoundError,
)
from tests.factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectFactory,
    ProjectRankingFactory,
    UserFactory,
)

query = DjangoReviewQuery()
handler = DjangoReviewHandler()


@pytest.mark.django_db
class TestListReviewerAssignments:
    def test_returns_assignments_for_user(self):
        user = UserFactory()
        assignment = CompetitionReviewerFactory(user=user)

        result = query.list_reviewer_assignments(user.id)

        assert len(result) == 1
        assert result[0].id == assignment.id

    def test_excludes_other_users(self):
        user = UserFactory()
        CompetitionReviewerFactory()

        result = query.list_reviewer_assignments(user.id)

        assert result == []


@pytest.mark.django_db
class TestGetReviewerAssignment:
    def test_returns_assignment_when_exists(self):
        user = UserFactory()
        assignment = CompetitionReviewerFactory(user=user)

        result = query.get_reviewer_assignment(user.id, assignment.competition_id)

        assert result is not None
        assert result.id == assignment.id

    def test_returns_none_when_not_found(self):
        user = UserFactory()

        result = query.get_reviewer_assignment(user.id, uuid4())

        assert result is None


@pytest.mark.django_db
class TestGetCompetitionWithProjects:
    def test_returns_competition(self):
        competition = CompetitionFactory()

        result = query.get_competition_with_projects(competition.id)

        assert result.id == competition.id

    def test_raises_for_nonexistent(self):
        with pytest.raises(ReviewNotFoundError):
            query.get_competition_with_projects(uuid4())


@pytest.mark.django_db
class TestGetReviewerRankings:
    def test_returns_rankings_dict(self):
        ranking = ProjectRankingFactory(position=1)

        result = query.get_reviewer_rankings(
            ranking.reviewer_id, ranking.competition_id
        )

        assert ranking.project_id in result
        assert result[ranking.project_id] == 1


@pytest.mark.django_db
class TestGetReviewProject:
    def test_returns_project_when_reviewer_has_access(self):
        user = UserFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        competition = CompetitionFactory()
        competition.projects.add(project)
        CompetitionReviewerFactory(user=user, competition=competition)

        result = query.get_review_project(user.id, project.id)

        assert result.id == project.id

    def test_raises_when_no_access(self):
        user = UserFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)

        with pytest.raises(ReviewNotFoundError):
            query.get_review_project(user.id, project.id)


@pytest.mark.django_db
class TestUpdateRankings:
    def test_creates_rankings(self):
        user = UserFactory()
        project1 = ProjectFactory(status=ProjectStatus.APPROVED)
        project2 = ProjectFactory(status=ProjectStatus.APPROVED)
        competition = CompetitionFactory()
        competition.projects.add(project1, project2)
        CompetitionReviewerFactory(user=user, competition=competition)

        handler.update_rankings(
            user_id=user.id,
            competition_id=competition.id,
            project_ids=[project1.id, project2.id],
        )

        rankings = query.get_reviewer_rankings(user.id, competition.id)
        assert rankings[project1.id] == 1
        assert rankings[project2.id] == 2

    def test_raises_for_completed_review(self):
        user = UserFactory()
        assignment = CompetitionReviewerFactory(
            user=user, status=ReviewStatus.COMPLETED
        )

        with pytest.raises(ReviewAlreadyCompletedError):
            handler.update_rankings(
                user_id=user.id,
                competition_id=assignment.competition_id,
                project_ids=[],
            )

    def test_raises_for_invalid_project_ids(self):
        user = UserFactory()
        competition = CompetitionFactory()
        CompetitionReviewerFactory(user=user, competition=competition)

        with pytest.raises(InvalidProjectIdsError):
            handler.update_rankings(
                user_id=user.id,
                competition_id=competition.id,
                project_ids=[uuid4()],
            )


@pytest.mark.django_db
class TestUpdateReviewStatus:
    def test_updates_status(self):
        user = UserFactory()
        assignment = CompetitionReviewerFactory(
            user=user, status=ReviewStatus.IN_PROGRESS
        )

        handler.update_review_status(
            user_id=user.id,
            competition_id=assignment.competition_id,
            status=ReviewStatus.COMPLETED,
        )

        assignment.refresh_from_db()
        assert assignment.status == ReviewStatus.COMPLETED

    def test_raises_for_nonexistent_assignment(self):
        user = UserFactory()

        with pytest.raises(ReviewNotFoundError):
            handler.update_review_status(
                user_id=user.id,
                competition_id=uuid4(),
                status=ReviewStatus.COMPLETED,
            )
