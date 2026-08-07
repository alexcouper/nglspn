"""The cron's entry point into the digest schedule.

Tests run on the immediate task backend (see `conftest._use_immediate_task_backend`),
so `call_command` runs the whole chain — command → task → handler. That is the
coupling worth protecting: the CronJobs name this CLI, and nothing else verifies
that a given `--kind`/`--cadence` reaches the digest it claims to.
"""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from hamcrest import assert_that, contains_string, equal_to

HANDLER = "services.notifications.django_impl.handler.DjangoNotificationHandler"


def run_enqueue_digest(kind: str, cadence: str) -> str:
    buffer = StringIO()
    call_command("enqueue_digest", "--kind", kind, "--cadence", cadence, stdout=buffer)
    return buffer.getvalue()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "cadence", "expected_task", "expected_digest"),
    [
        ("discussion", "hourly", "send_discussion_digest_hourly", "hourly"),
        ("discussion", "daily", "send_discussion_digest_daily", "daily"),
        ("article", "hourly", "send_article_digest_hourly", "hourly"),
        ("article", "daily", "send_article_digest_daily", "daily"),
        ("article", "weekly", "send_article_digest_weekly", "weekly"),
    ],
)
def test_each_combination_reaches_its_own_digest(
    kind, cadence, expected_task, expected_digest
):
    with patch(f"{HANDLER}.send_{kind}_digest") as mock_digest:
        output = run_enqueue_digest(kind, cadence)

    mock_digest.assert_called_once_with(expected_digest)
    assert_that(output, contains_string(expected_task))


@pytest.mark.django_db
def test_a_discussion_cadence_does_not_trigger_the_article_digest():
    with (
        patch(f"{HANDLER}.send_discussion_digest"),
        patch(f"{HANDLER}.send_article_digest") as mock_article,
    ):
        run_enqueue_digest("discussion", "hourly")

    assert_that(mock_article.call_count, equal_to(0))


def test_discussion_weekly_is_rejected_because_no_such_cadence_exists():
    with pytest.raises(CommandError) as excinfo:
        run_enqueue_digest("discussion", "weekly")

    assert_that(str(excinfo.value), contains_string("discussion"))
    assert_that(str(excinfo.value), contains_string("weekly"))


def test_unknown_kind_is_rejected():
    with pytest.raises(CommandError):
        run_enqueue_digest("banana", "hourly")


def test_unknown_cadence_is_rejected():
    with pytest.raises(CommandError):
        run_enqueue_digest("article", "yearly")


def test_never_is_not_an_enqueueable_cadence():
    with pytest.raises(CommandError):
        run_enqueue_digest("article", "never")


def test_both_arguments_are_required():
    with pytest.raises(CommandError):
        call_command("enqueue_digest", "--kind", "article")
