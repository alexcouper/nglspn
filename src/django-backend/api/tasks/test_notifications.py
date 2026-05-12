import logging
from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from api.tasks.notifications import delete_old_read_notifications


@pytest.mark.django_db
def test_delete_old_read_notifications_invokes_handler() -> None:
    with patch(
        "services.notifications.django_impl.handler"
        ".DjangoNotificationHandler"
        ".delete_old_read_notifications",
        return_value=0,
    ) as handler_call:
        delete_old_read_notifications.func()

    assert_that(handler_call.called, equal_to(True))


@pytest.mark.django_db
def test_delete_old_read_notifications_logs_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch(
            "services.notifications.django_impl.handler"
            ".DjangoNotificationHandler"
            ".delete_old_read_notifications",
            return_value=7,
        ),
        caplog.at_level(logging.INFO, logger="api.tasks.notifications"),
    ):
        delete_old_read_notifications.func()

    assert_that(
        any("removed 7 rows" in record.message for record in caplog.records),
        equal_to(True),
    )
