import uuid

from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_key,
    not_,
)

from tests.factories import UserFactory


class TestEmailPreferences:
    def test_new_user_has_email_preferences_opted_in_by_default(self, db) -> None:
        user = UserFactory()

        assert_that(user.email_opt_in_competition_results, equal_to(True))
        assert_that(user.email_opt_in_platform_updates, equal_to(True))

    def test_update_email_preferences_via_api(self, client, user, auth_headers) -> None:
        response = client.put(
            "/api/auth/me",
            data={
                "email_opt_in_competition_results": False,
                "email_opt_in_platform_updates": False,
            },
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        user.refresh_from_db()
        assert_that(user.email_opt_in_competition_results, equal_to(False))
        assert_that(user.email_opt_in_platform_updates, equal_to(False))

    def test_get_me_returns_email_preferences(self, client, user, auth_headers) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                email_opt_in_competition_results=True,
                email_opt_in_platform_updates=True,
            ),
        )


class TestExternalPromotionPreference:
    def test_new_user_has_external_promotions_opted_in_by_default(self, db) -> None:
        user = UserFactory()

        assert_that(user.opt_in_to_external_promotions, equal_to(True))

    def test_update_external_promotion_preference_via_api(
        self, client, user, auth_headers
    ) -> None:
        response = client.put(
            "/api/auth/me",
            data={"opt_in_to_external_promotions": False},
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        user.refresh_from_db()
        assert_that(user.opt_in_to_external_promotions, equal_to(False))

    def test_get_me_returns_external_promotion_preference(
        self, client, user, auth_headers
    ) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(opt_in_to_external_promotions=True),
        )


class TestPublicProfile:
    def test_get_public_profile_returns_only_public_fields(self, client, user) -> None:
        user.first_name = "John"
        user.last_name = "Doe"
        user.info = "A passionate developer"
        user.save()

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(user.id),
                first_name="John",
                last_name="Doe",
                info="A passionate developer",
            ),
        )
        # This check ensures no extra fields are returned
        assert_that(
            list(response.json().keys()),
            contains_inanyorder("id", "first_name", "last_name", "info"),
        )

    def test_get_public_profile_does_not_leak_private_settings(
        self, client, user
    ) -> None:
        response = client.get(f"/api/users/{user.id}")

        data = response.json()
        assert_that(data, not_(has_key("email")))
        assert_that(data, not_(has_key("email_opt_in_competition_results")))
        assert_that(data, not_(has_key("email_opt_in_platform_updates")))
        assert_that(data, not_(has_key("opt_in_to_external_promotions")))

    def test_get_public_profile_nonexistent_user_returns_404(self, client, db) -> None:
        fake_id = uuid.uuid4()
        response = client.get(f"/api/users/{fake_id}")

        assert_that(response.status_code, equal_to(404))
        assert_that(response.json(), has_entries(detail="User not found"))

    def test_get_public_profile_with_empty_info(self, client, db) -> None:
        user = UserFactory(first_name="Jane", last_name="Smith", info="")

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                first_name="Jane",
                last_name="Smith",
                info="",
            ),
        )
