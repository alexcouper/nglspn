from unittest.mock import patch

import pytest
from hamcrest import assert_that, calling, equal_to, raises

from apps.projects.models import (
    CompetitionReviewer,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
)
from services.review.django_impl.handler import DjangoReviewHandler
from services.review.exceptions import (
    DuplicateProjectError,
    ProjectNotInCompetitionError,
    ReviewClosedError,
    ReviewerNotAssignedError,
)
from tests.factories import (
    CompetitionFactory,
    CompetitionReviewerFactory,
    ProjectFactory,
    ProjectRankingFactory,
    UserFactory,
)


@pytest.fixture
def handler():
    return DjangoReviewHandler()


def _status_of(reviewer: CompetitionReviewer) -> str:
    reviewer.refresh_from_db()
    return reviewer.status


def competition_with_reviewer(project_count=3, status=ReviewStatus.IN_PROGRESS):
    projects = [ProjectFactory() for _ in range(project_count)]
    competition = CompetitionFactory(projects=projects)
    reviewer = UserFactory()
    CompetitionReviewerFactory(competition=competition, user=reviewer, status=status)
    return competition, reviewer, projects


def saved_ballot(competition, reviewer):
    return [
        row.project_id
        for row in ProjectRanking.objects.filter(
            reviewer=reviewer, competition=competition
        ).order_by("position")
    ]


def save_ballot(competition, reviewer, projects):
    for position, project in enumerate(projects, start=1):
        ProjectRankingFactory(
            reviewer=reviewer,
            competition=competition,
            project=project,
            position=position,
        )


@pytest.mark.django_db
class TestEndReviewPeriod:
    def test_transitions_in_progress_reviews_to_ended(self, handler) -> None:
        competition = CompetitionFactory()
        in_progress = CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.IN_PROGRESS
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(1))
        assert_that(_status_of(in_progress), equal_to(ReviewStatus.ENDED))

    def test_leaves_completed_reviews_untouched(self, handler) -> None:
        competition = CompetitionFactory()
        completed = CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.COMPLETED
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(0))
        assert_that(_status_of(completed), equal_to(ReviewStatus.COMPLETED))

    def test_leaves_already_ended_reviews_untouched(self, handler) -> None:
        competition = CompetitionFactory()
        already_ended = CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.ENDED
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(0))
        assert_that(_status_of(already_ended), equal_to(ReviewStatus.ENDED))

    def test_does_not_affect_other_competitions(self, handler) -> None:
        target = CompetitionFactory()
        other = CompetitionFactory()
        CompetitionReviewerFactory(competition=target, status=ReviewStatus.IN_PROGRESS)
        other_reviewer = CompetitionReviewerFactory(
            competition=other, status=ReviewStatus.IN_PROGRESS
        )

        handler.end_review_period(target.id)

        assert_that(_status_of(other_reviewer), equal_to(ReviewStatus.IN_PROGRESS))

    def test_counts_all_in_progress_rows_for_competition(self, handler) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.IN_PROGRESS
        )
        CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.IN_PROGRESS
        )
        CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.COMPLETED
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(2))


@pytest.mark.django_db
class TestReplaceBallot:
    def test_stores_one_row_per_submitted_project_numbered_from_one(
        self, handler
    ) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        first, second = projects[1], projects[0]

        handler.replace_ballot(reviewer.id, competition.id, [first.id, second.id])

        assert_that(
            saved_ballot(competition, reviewer), equal_to([first.id, second.id])
        )
        positions = list(
            ProjectRanking.objects.filter(reviewer=reviewer)
            .order_by("position")
            .values_list("position", flat=True)
        )
        assert_that(positions, equal_to([1, 2]))

    def test_replaces_the_previous_ballot(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        save_ballot(competition, reviewer, projects)

        handler.replace_ballot(reviewer.id, competition.id, [projects[2].id])

        assert_that(saved_ballot(competition, reviewer), equal_to([projects[2].id]))

    def test_empty_list_clears_the_ballot(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        save_ballot(competition, reviewer, projects)

        handler.replace_ballot(reviewer.id, competition.id, [])

        assert_that(saved_ballot(competition, reviewer), equal_to([]))

    def test_leaves_other_reviewers_ballots_alone(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        other = UserFactory()
        CompetitionReviewerFactory(competition=competition, user=other)
        save_ballot(competition, other, projects)

        handler.replace_ballot(reviewer.id, competition.id, [projects[0].id])

        assert_that(
            saved_ballot(competition, other), equal_to([p.id for p in projects])
        )

    def test_duplicate_project_ids_are_rejected_before_any_write(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        save_ballot(competition, reviewer, projects)
        repeated = [projects[0].id, projects[1].id, projects[0].id]

        assert_that(
            calling(handler.replace_ballot).with_args(
                reviewer.id, competition.id, repeated
            ),
            raises(DuplicateProjectError),
        )
        assert_that(
            saved_ballot(competition, reviewer), equal_to([p.id for p in projects])
        )

    def test_a_failed_write_leaves_the_previous_ballot_intact(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        save_ballot(competition, reviewer, projects)

        with (
            patch.object(
                ProjectRanking.objects, "bulk_create", side_effect=OSError("db gone")
            ),
            pytest.raises(OSError, match="db gone"),
        ):
            handler.replace_ballot(reviewer.id, competition.id, [projects[0].id])

        assert_that(
            saved_ballot(competition, reviewer), equal_to([p.id for p in projects])
        )

    def test_projects_outside_the_competition_are_rejected(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        outsider = ProjectFactory()

        assert_that(
            calling(handler.replace_ballot).with_args(
                reviewer.id, competition.id, [projects[0].id, outsider.id]
            ),
            raises(ProjectNotInCompetitionError),
        )
        assert_that(saved_ballot(competition, reviewer), equal_to([]))

    def test_rejected_projects_are_not_rankable(self, handler) -> None:
        competition, reviewer, _projects = competition_with_reviewer()
        rejected = ProjectFactory(status=ProjectStatus.REJECTED)
        competition.projects.add(rejected)

        assert_that(
            calling(handler.replace_ballot).with_args(
                reviewer.id, competition.id, [rejected.id]
            ),
            raises(ProjectNotInCompetitionError),
        )

    def test_a_completed_review_cannot_be_changed(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer(
            status=ReviewStatus.COMPLETED
        )

        assert_that(
            calling(handler.replace_ballot).with_args(
                reviewer.id, competition.id, [projects[0].id]
            ),
            raises(ReviewClosedError),
        )

    def test_an_ended_review_cannot_be_changed(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer(
            status=ReviewStatus.ENDED
        )

        assert_that(
            calling(handler.replace_ballot).with_args(
                reviewer.id, competition.id, [projects[0].id]
            ),
            raises(ReviewClosedError),
        )

    def test_a_non_reviewer_cannot_submit_a_ballot(self, handler) -> None:
        competition, _reviewer, projects = competition_with_reviewer()
        stranger = UserFactory()

        assert_that(
            calling(handler.replace_ballot).with_args(
                stranger.id, competition.id, [projects[0].id]
            ),
            raises(ReviewerNotAssignedError),
        )
