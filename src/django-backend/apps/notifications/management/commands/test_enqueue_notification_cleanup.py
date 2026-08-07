from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from hamcrest import assert_that, contains_string

HANDLER = "services.notifications.django_impl.handler.DjangoNotificationHandler"


@pytest.mark.django_db
def test_reaches_the_cleanup_handler():
    buffer = StringIO()

    with patch(
        f"{HANDLER}.delete_old_read_notifications", return_value=0
    ) as mock_cleanup:
        call_command("enqueue_notification_cleanup", stdout=buffer)

    mock_cleanup.assert_called_once_with()
    assert_that(buffer.getvalue(), contains_string("delete_old_read_notifications"))
