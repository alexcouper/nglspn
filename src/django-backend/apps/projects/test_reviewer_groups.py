import pytest
from django.db.models import ProtectedError
from hamcrest import assert_that, equal_to, is_

from apps.projects.models import (
    EVERYONE_REVIEWER_GROUP_NAME,
    ReviewerGroup,
)
from tests.factories import CompetitionFactory, ReviewerGroupFactory


def _everyone() -> ReviewerGroup:
    return ReviewerGroup.objects.get(name=EVERYONE_REVIEWER_GROUP_NAME)


@pytest.mark.django_db
class TestEveryoneGroup:
    def test_is_seeded_by_migrations_and_includes_all_users(self) -> None:
        assert_that(_everyone().includes_all_users, is_(True))

    def test_is_the_reviewer_group_of_a_competition_created_without_one(
        self,
    ) -> None:
        competition = CompetitionFactory()

        assert_that(competition.reviewer_group, equal_to(_everyone()))


@pytest.mark.django_db
class TestPanel:
    def test_cannot_be_deleted_while_a_competition_uses_it(self) -> None:
        panel = ReviewerGroupFactory()
        CompetitionFactory(reviewer_group=panel)

        with pytest.raises(ProtectedError):
            panel.delete()

        assert_that(ReviewerGroup.objects.filter(pk=panel.pk).exists(), is_(True))
