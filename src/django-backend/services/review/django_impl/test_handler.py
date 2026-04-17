import pytest
from hamcrest import assert_that, equal_to

from apps.projects.models import CompetitionReviewer, ReviewStatus
from services.review.django_impl.handler import DjangoReviewHandler
from tests.factories import CompetitionFactory, CompetitionReviewerFactory


@pytest.fixture
def handler():
    return DjangoReviewHandler()


def _status_of(reviewer: CompetitionReviewer) -> str:
    reviewer.refresh_from_db()
    return reviewer.status


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
