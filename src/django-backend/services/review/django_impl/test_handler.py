from unittest.mock import patch

import pytest
from hamcrest import assert_that, calling, equal_to, has_length, raises

from apps.projects.models import (
    CompetitionReviewer,
    CompetitionStatus,
    ProjectRanking,
    ProjectStatus,
    ReviewStatus,
)
from services.review.django_impl.handler import DjangoReviewHandler
from services.review.django_impl.query import DjangoReviewQuery
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
    ReviewerGroupFactory,
    UserFactory,
    review_of,
    voting_competition,
)


@pytest.fixture
def handler():
    return DjangoReviewHandler()


def _status_of(reviewer: CompetitionReviewer) -> str:
    reviewer.refresh_from_db()
    return reviewer.status


def competition_with_reviewer(project_count=3, status=ReviewStatus.IN_PROGRESS):
    """A voting competition with a review the reviewer has already started."""
    projects = [ProjectFactory() for _ in range(project_count)]
    competition = voting_competition(projects=projects)
    reviewer = UserFactory()
    review_of(reviewer, competition, status=status)
    return competition, reviewer, projects


def reviews_of(user) -> list[tuple]:
    return list(
        CompetitionReviewer.objects.filter(user=user).values_list(
            "competition_id", "status"
        )
    )


def close(competition) -> None:
    competition.status = CompetitionStatus.CLOSED
    competition.save()


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

    def test_a_review_in_a_competition_that_left_voting_cannot_be_changed(
        self, handler
    ) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        save_ballot(competition, reviewer, projects)
        close(competition)

        assert_that(
            calling(handler.replace_ballot).with_args(
                reviewer.id, competition.id, [projects[0].id]
            ),
            raises(ReviewClosedError),
        )
        assert_that(
            saved_ballot(competition, reviewer), equal_to([p.id for p in projects])
        )

    def test_a_panel_outsider_cannot_submit_a_ballot(self, handler) -> None:
        project = ProjectFactory()
        panel = ReviewerGroupFactory(members=[UserFactory()])
        competition = voting_competition(group=panel, projects=[project])
        outsider = UserFactory()

        assert_that(
            calling(handler.replace_ballot).with_args(
                outsider.id, competition.id, [project.id]
            ),
            raises(ReviewerNotAssignedError),
        )
        assert_that(reviews_of(outsider), equal_to([]))

    def test_nobody_can_submit_before_voting_opens(self, handler) -> None:
        project = ProjectFactory()
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS, projects=[project]
        )

        assert_that(
            calling(handler.replace_ballot).with_args(
                UserFactory().id, competition.id, [project.id]
            ),
            raises(ReviewerNotAssignedError),
        )

    def test_the_first_ballot_starts_the_review(self, handler) -> None:
        first, second = ProjectFactory(), ProjectFactory()
        competition = voting_competition(projects=[first, second])
        newcomer = UserFactory()

        handler.replace_ballot(newcomer.id, competition.id, [second.id, first.id])

        assert_that(
            reviews_of(newcomer),
            equal_to([(competition.id, ReviewStatus.IN_PROGRESS)]),
        )
        assert_that(
            saved_ballot(competition, newcomer), equal_to([second.id, first.id])
        )

    def test_a_rejected_first_ballot_starts_no_review(self, handler) -> None:
        project = ProjectFactory()
        competition = voting_competition(projects=[project])
        newcomer = UserFactory()

        assert_that(
            calling(handler.replace_ballot).with_args(
                newcomer.id, competition.id, [project.id, project.id]
            ),
            raises(DuplicateProjectError),
        )
        assert_that(reviews_of(newcomer), equal_to([]))

    def test_saving_twice_keeps_one_review(self, handler) -> None:
        project = ProjectFactory()
        competition = voting_competition(projects=[project])
        newcomer = UserFactory()

        handler.replace_ballot(newcomer.id, competition.id, [project.id])
        handler.replace_ballot(newcomer.id, competition.id, [])

        assert_that(reviews_of(newcomer), has_length(1))


@pytest.mark.django_db
class TestSetReviewStatus:
    def test_completing_without_a_ballot_is_a_counted_abstention(self, handler) -> None:
        competition = voting_competition(projects=[ProjectFactory()])
        abstainer = UserFactory()

        handler.set_review_status(abstainer.id, competition.id, ReviewStatus.COMPLETED)

        assert_that(
            reviews_of(abstainer),
            equal_to([(competition.id, ReviewStatus.COMPLETED)]),
        )
        tally = DjangoReviewQuery().get_competition_tally(competition.id)
        assert_that(tally.counted_ballots, equal_to(1))

    def test_reopening_a_completed_review(self, handler) -> None:
        competition, reviewer, _ = competition_with_reviewer(
            status=ReviewStatus.COMPLETED
        )

        handler.set_review_status(reviewer.id, competition.id, ReviewStatus.IN_PROGRESS)

        assert_that(
            reviews_of(reviewer),
            equal_to([(competition.id, ReviewStatus.IN_PROGRESS)]),
        )

    def test_cannot_change_once_the_competition_left_voting(self, handler) -> None:
        competition, reviewer, _ = competition_with_reviewer()
        close(competition)

        assert_that(
            calling(handler.set_review_status).with_args(
                reviewer.id, competition.id, ReviewStatus.COMPLETED
            ),
            raises(ReviewClosedError),
        )
        assert_that(
            reviews_of(reviewer),
            equal_to([(competition.id, ReviewStatus.IN_PROGRESS)]),
        )

    def test_assigning_a_winner_closes_the_review(self, handler) -> None:
        competition, reviewer, projects = competition_with_reviewer()
        competition.winner = projects[0]
        competition.save()

        assert_that(
            calling(handler.set_review_status).with_args(
                reviewer.id, competition.id, ReviewStatus.COMPLETED
            ),
            raises(ReviewClosedError),
        )

    def test_a_panel_outsider_gets_no_review(self, handler) -> None:
        panel = ReviewerGroupFactory(members=[UserFactory()])
        competition = voting_competition(group=panel)
        outsider = UserFactory()

        assert_that(
            calling(handler.set_review_status).with_args(
                outsider.id, competition.id, ReviewStatus.COMPLETED
            ),
            raises(ReviewerNotAssignedError),
        )
        assert_that(reviews_of(outsider), equal_to([]))
