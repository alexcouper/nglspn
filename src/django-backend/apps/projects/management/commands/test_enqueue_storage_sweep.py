from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from hamcrest import assert_that, contains_string

from services.images.handler_interface import StorageSweepResult

HANDLER = "services.images.django_impl.handler.DjangoImageHandler"
NOTHING_TO_DO = StorageSweepResult(
    pending_uploads_reaped=0, objects_deleted=0, failures=0
)


@pytest.mark.django_db
def test_reaches_the_sweep_handler():
    buffer = StringIO()

    with patch(
        f"{HANDLER}.sweep_orphaned_objects", return_value=NOTHING_TO_DO
    ) as mock_sweep:
        call_command("enqueue_storage_sweep", stdout=buffer)

    mock_sweep.assert_called_once_with(batch_size=500)
    assert_that(buffer.getvalue(), contains_string("sweep_orphaned_storage_objects"))


@pytest.mark.django_db
def test_batch_size_reaches_the_handler():
    with patch(
        f"{HANDLER}.sweep_orphaned_objects", return_value=NOTHING_TO_DO
    ) as mock_sweep:
        call_command("enqueue_storage_sweep", "--batch-size", "10", stdout=StringIO())

    mock_sweep.assert_called_once_with(batch_size=10)
