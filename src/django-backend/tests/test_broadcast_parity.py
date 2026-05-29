import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.emails.broadcast_parity import check_parity
from tests.factories import make_broadcast_follower


@pytest.mark.django_db
class TestCheckParity:
    def test_matches_when_legacy_and_new_agree(self):
        # Follows the channel (new path) and keeps the legacy flag on.
        make_broadcast_follower(
            "platform_updates",
            email_enabled=True,
            email_opt_in_platform_updates=True,
        )

        result = check_parity("platform_updates")

        assert result.matches

    def test_detects_legacy_only_recipient(self):
        # Legacy flag on, but channel email disabled → legacy-only.
        legacy_only = make_broadcast_follower(
            "platform_updates",
            email_enabled=False,
            email_opt_in_platform_updates=True,
        )

        result = check_parity("platform_updates")

        assert legacy_only.id in result.only_legacy
        assert not result.matches

    def test_detects_new_only_recipient(self):
        # Channel email on, but legacy flag off → new-only.
        new_only = make_broadcast_follower(
            "platform_updates",
            email_enabled=True,
            email_opt_in_platform_updates=False,
        )

        result = check_parity("platform_updates")

        assert new_only.id in result.only_new
        assert not result.matches


@pytest.mark.django_db
class TestCheckBroadcastParityCommand:
    def test_succeeds_when_in_parity(self):
        # competition_results kept empty on both sides so the command (which
        # checks every email_type) sees full parity.
        make_broadcast_follower(
            "platform_updates",
            email_enabled=True,
            email_opt_in_platform_updates=True,
            email_opt_in_competition_results=False,
        )

        call_command("check_broadcast_parity")

    def test_raises_on_divergence(self):
        make_broadcast_follower(
            "platform_updates",
            email_enabled=False,
            email_opt_in_platform_updates=True,
            email_opt_in_competition_results=False,
        )

        with pytest.raises(CommandError):
            call_command("check_broadcast_parity")
