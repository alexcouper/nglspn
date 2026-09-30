import pytest
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from django.urls import reverse
from hamcrest import assert_that, equal_to, is_

from apps.projects.admin import ReviewerGroupAdmin
from apps.projects.models import EVERYONE_REVIEWER_GROUP_NAME, ReviewerGroup
from tests.factories import CompetitionFactory, ReviewerGroupFactory, UserFactory


def _superuser_request() -> HttpRequest:
    request = HttpRequest()
    request.user = UserFactory.build(is_superuser=True, is_staff=True)
    return request


def _can_delete(group: ReviewerGroup) -> bool:
    admin = ReviewerGroupAdmin(ReviewerGroup, AdminSite())
    return admin.has_delete_permission(_superuser_request(), group)


def _change_page(admin_client, competition) -> str:
    url = reverse("admin:projects_competition_change", args=[competition.pk])
    response = admin_client.get(url)
    assert_that(response.status_code, equal_to(200))
    return response.content.decode()


@pytest.mark.django_db
class TestReviewerGroupAdmin:
    def test_everyone_cannot_be_deleted(self) -> None:
        everyone = ReviewerGroup.objects.get(name=EVERYONE_REVIEWER_GROUP_NAME)

        assert_that(_can_delete(everyone), is_(False))

    def test_an_unused_panel_can_be_deleted(self) -> None:
        assert_that(_can_delete(ReviewerGroupFactory()), is_(True))


@pytest.mark.django_db
class TestCompetitionChangePage:
    def test_offers_the_reviewer_group(self, admin_client) -> None:
        page = _change_page(admin_client, CompetitionFactory())

        assert_that('name="reviewer_group"' in page, is_(True))

    def test_has_no_manual_reviewer_assignment(self, admin_client) -> None:
        page = _change_page(admin_client, CompetitionFactory())

        assert_that("_add_all_reviewers" in page, is_(False))
        assert_that("View Voting Results" in page, is_(True))

    def test_list_offers_no_end_review_period_action(self, admin_client) -> None:
        CompetitionFactory()

        response = admin_client.get(reverse("admin:projects_competition_changelist"))

        assert_that("end_review_period" in response.content.decode(), is_(False))
