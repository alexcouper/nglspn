import pytest
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from hamcrest import assert_that, contains_string, equal_to

from apps.projects.admin import CompetitionAdmin
from apps.projects.models import Competition, ReviewStatus
from tests.factories import CompetitionFactory, CompetitionReviewerFactory, UserFactory


def _make_request() -> HttpRequest:
    request = HttpRequest()
    request.user = UserFactory.build(is_superuser=True, is_staff=True)
    return request


@pytest.fixture
def admin_instance():
    return CompetitionAdmin(Competition, AdminSite())


@pytest.mark.django_db
class TestEndReviewPeriodAction:
    def test_transitions_in_progress_reviews_for_selected_competitions(
        self, admin_instance, monkeypatch
    ) -> None:
        comp_a = CompetitionFactory()
        comp_b = CompetitionFactory()
        in_progress_a = CompetitionReviewerFactory(
            competition=comp_a, status=ReviewStatus.IN_PROGRESS
        )
        in_progress_b = CompetitionReviewerFactory(
            competition=comp_b, status=ReviewStatus.IN_PROGRESS
        )
        completed = CompetitionReviewerFactory(
            competition=comp_a, status=ReviewStatus.COMPLETED
        )

        request = _make_request()
        captured: list[str] = []
        monkeypatch.setattr(
            admin_instance,
            "message_user",
            lambda req, msg, *a, **kw: captured.append(msg),
        )

        queryset = Competition.objects.filter(id__in=[comp_a.id, comp_b.id])
        admin_instance.end_review_period(request, queryset)

        in_progress_a.refresh_from_db()
        in_progress_b.refresh_from_db()
        completed.refresh_from_db()

        assert_that(in_progress_a.status, equal_to(ReviewStatus.ENDED))
        assert_that(in_progress_b.status, equal_to(ReviewStatus.ENDED))
        assert_that(completed.status, equal_to(ReviewStatus.COMPLETED))
        assert_that(len(captured), equal_to(1))
        assert_that(captured[0], contains_string("2"))

    def test_leaves_unselected_competition_rows_alone(
        self, admin_instance, monkeypatch
    ) -> None:
        selected = CompetitionFactory()
        unselected = CompetitionFactory()
        CompetitionReviewerFactory(
            competition=selected, status=ReviewStatus.IN_PROGRESS
        )
        untouched = CompetitionReviewerFactory(
            competition=unselected, status=ReviewStatus.IN_PROGRESS
        )

        request = _make_request()
        monkeypatch.setattr(admin_instance, "message_user", lambda *a, **kw: None)

        queryset = Competition.objects.filter(id=selected.id)
        admin_instance.end_review_period(request, queryset)

        untouched.refresh_from_db()
        assert_that(untouched.status, equal_to(ReviewStatus.IN_PROGRESS))
