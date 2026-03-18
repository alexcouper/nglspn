from unittest.mock import patch

import pytest
from hamcrest import assert_that, empty, equal_to, has_length

from services.registration.django_impl.handler import DjangoRegistrationHandler
from services.registration.steps import ONBOARDING_STEPS, OnboardingStep
from tests.factories import UserFactory


@pytest.fixture
def handler():
    return DjangoRegistrationHandler()


@pytest.mark.django_db
class TestGetPendingSteps:
    def test_verified_user_has_no_pending_steps(self, handler) -> None:
        user = UserFactory(is_verified=True)

        result = handler.get_pending_steps(user)

        assert_that(result, empty())

    def test_unverified_user_has_verify_email_step(self, handler) -> None:
        user = UserFactory(is_verified=False)

        result = handler.get_pending_steps(user)

        assert_that(result, has_length(1))
        assert_that(result[0].id, equal_to("verify-email"))

    def test_steps_returned_in_priority_order(self, handler) -> None:
        user = UserFactory(is_verified=False)

        extra_steps = [
            *ONBOARDING_STEPS,
            OnboardingStep(
                id="always-pending",
                priority=50,
                check=lambda u: False,
            ),
        ]

        with patch(
            "services.registration.django_impl.handler.ONBOARDING_STEPS",
            extra_steps,
        ):
            result = handler.get_pending_steps(user)

        assert_that(result, has_length(2))
        assert_that(result[0].id, equal_to("always-pending"))
        assert_that(result[1].id, equal_to("verify-email"))

    def test_new_step_surfaces_for_existing_user(self, handler) -> None:
        user = UserFactory(is_verified=True)

        extra_steps = [
            *ONBOARDING_STEPS,
            OnboardingStep(
                id="new-requirement",
                priority=200,
                check=lambda u: False,
            ),
        ]

        with patch(
            "services.registration.django_impl.handler.ONBOARDING_STEPS",
            extra_steps,
        ):
            result = handler.get_pending_steps(user)

        assert_that(result, has_length(1))
        assert_that(result[0].id, equal_to("new-requirement"))

    def test_user_with_no_names_has_complete_profile_step(self, handler) -> None:
        user = UserFactory(is_verified=True, first_name="", last_name="")

        result = handler.get_pending_steps(user)

        assert_that(result, has_length(1))
        assert_that(result[0].id, equal_to("complete-profile"))

    def test_user_with_first_name_only_skips_complete_profile(self, handler) -> None:
        user = UserFactory(is_verified=True, first_name="Jane", last_name="")

        result = handler.get_pending_steps(user)

        assert_that(result, empty())

    def test_user_with_last_name_only_skips_complete_profile(self, handler) -> None:
        user = UserFactory(is_verified=True, first_name="", last_name="Doe")

        result = handler.get_pending_steps(user)

        assert_that(result, empty())

    def test_user_with_both_names_skips_complete_profile(self, handler) -> None:
        user = UserFactory(is_verified=True, first_name="Jane", last_name="Doe")

        result = handler.get_pending_steps(user)

        assert_that(result, empty())

    def test_whitespace_only_names_treated_as_empty(self, handler) -> None:
        user = UserFactory(is_verified=True, first_name="  ", last_name="")

        result = handler.get_pending_steps(user)

        assert_that(result, has_length(1))
        assert_that(result[0].id, equal_to("complete-profile"))

    def test_complete_profile_ordered_after_verify_email(self, handler) -> None:
        user = UserFactory(is_verified=False, first_name="", last_name="")

        result = handler.get_pending_steps(user)

        assert_that(result, has_length(2))
        assert_that(result[0].id, equal_to("verify-email"))
        assert_that(result[1].id, equal_to("complete-profile"))

    def test_completed_steps_are_excluded(self, handler) -> None:
        user = UserFactory(is_verified=True)

        extra_steps = [
            *ONBOARDING_STEPS,
            OnboardingStep(
                id="always-done",
                priority=50,
                check=lambda u: True,
            ),
        ]

        with patch(
            "services.registration.django_impl.handler.ONBOARDING_STEPS",
            extra_steps,
        ):
            result = handler.get_pending_steps(user)

        assert_that(result, empty())
