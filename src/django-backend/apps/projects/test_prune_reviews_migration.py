from importlib import import_module

import pytest
from django.apps import apps as django_apps
from hamcrest import assert_that, contains_inanyorder, equal_to, is_

from apps.projects.models import (
    EVERYONE_REVIEWER_GROUP_NAME,
    CompetitionReviewer,
    ProjectRanking,
    ReviewerGroup,
)
from services import REPO
from tests.factories import CompetitionFactory, ProjectFactory, UserFactory, review_of

migration_module = import_module(
    "apps.projects.migrations.0054_seed_reviewer_groups_and_prune_reviews"
)

# Written straight to the column: the model no longer offers the choice.
LEGACY_ENDED = "ended"


def _run_prune() -> None:
    migration_module.prune_assignment_only_reviews(django_apps, schema_editor=None)


def _legacy_ended(review: CompetitionReviewer) -> CompetitionReviewer:
    CompetitionReviewer.objects.filter(pk=review.pk).update(status=LEGACY_ENDED)
    return review


def _surviving_reviewers(competition) -> list:
    return list(
        CompetitionReviewer.objects.filter(competition=competition).values_list(
            "user_id", "status"
        )
    )


def _tally_summary(competition) -> tuple:
    tally = REPO.reviews.get_competition_tally(competition.pk)
    return tally.counted_ballots, tally.tiers


@pytest.mark.django_db
class TestPruneAssignmentOnlyReviews:
    @pytest.fixture
    def competition_with_every_kind_of_review(self):
        first, second = ProjectFactory(), ProjectFactory()
        competition = CompetitionFactory(projects=[first, second])
        users = {
            name: UserFactory()
            for name in (
                "untouched",
                "untouched_ended",
                "ended_with_rankings",
                "completed_with_rankings",
                "abstained",
            )
        }
        review_of(users["untouched"], competition)
        _legacy_ended(review_of(users["untouched_ended"], competition))
        _legacy_ended(
            review_of(users["ended_with_rankings"], competition, ranked=[second])
        )
        review_of(
            users["completed_with_rankings"],
            competition,
            status="completed",
            ranked=[first, second],
        )
        review_of(users["abstained"], competition, status="completed")
        return competition, users

    def test_deletes_rows_that_were_only_assignments(
        self, competition_with_every_kind_of_review
    ) -> None:
        competition, users = competition_with_every_kind_of_review

        _run_prune()

        assert_that(
            _surviving_reviewers(competition),
            contains_inanyorder(
                (users["ended_with_rankings"].id, "in_progress"),
                (users["completed_with_rankings"].id, "completed"),
                (users["abstained"].id, "completed"),
            ),
        )

    def test_keeps_every_ranking(self, competition_with_every_kind_of_review) -> None:
        competition, _ = competition_with_every_kind_of_review
        rankings_before = ProjectRanking.objects.filter(competition=competition).count()

        _run_prune()

        assert_that(
            ProjectRanking.objects.filter(competition=competition).count(),
            equal_to(rankings_before),
        )

    def test_leaves_the_tally_unchanged(
        self, competition_with_every_kind_of_review
    ) -> None:
        competition, _ = competition_with_every_kind_of_review
        before = _tally_summary(competition)

        _run_prune()

        assert_that(_tally_summary(competition), equal_to(before))


@pytest.mark.django_db
class TestSeedEveryone:
    def test_creates_everyone_when_it_is_missing(self) -> None:
        ReviewerGroup.objects.filter(name=EVERYONE_REVIEWER_GROUP_NAME).delete()

        migration_module.seed_everyone_and_backfill(django_apps, schema_editor=None)

        everyone = ReviewerGroup.objects.get(name=EVERYONE_REVIEWER_GROUP_NAME)
        assert_that(everyone.includes_all_users, is_(True))

    def test_is_idempotent(self) -> None:
        migration_module.seed_everyone_and_backfill(django_apps, schema_editor=None)

        assert_that(
            ReviewerGroup.objects.filter(name=EVERYONE_REVIEWER_GROUP_NAME).count(),
            equal_to(1),
        )
