"""The tombstone-and-sweep path that keeps deleted rows from orphaning S3 objects.

`ProjectImage` rows disappear by cascade from `Article` and from `Project`, not
only by an explicit `delete_image`, and a queryset `.delete()` bypasses any model
`delete()` override. So the keys are recorded by `pre_delete` receivers and drained
out of band. These tests pin both halves, plus the cascade cases that Django's
fast-delete optimisation would silently break if the receivers were ever removed.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.projects.models import (
    ImageVariant,
    OrphanedStorageObject,
    ProjectImage,
    UploadStatus,
    VariantSize,
)
from services import HANDLERS
from services.images.django_impl.handler import DjangoImageHandler
from services.images.handler_interface import (
    MAX_SWEEP_ATTEMPTS,
    PENDING_UPLOAD_MAX_AGE_HOURS,
)
from tests.factories import (
    ArticleFactory,
    ProjectFactory,
    ProjectImageFactory,
    article_image,
)

DELETE_OBJECT = "services.storage.storage_service.delete_object"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


@pytest.fixture
def handler():
    return DjangoImageHandler()


def make_variant(image: ProjectImage, size: str = VariantSize.THUMB) -> ImageVariant:
    return ImageVariant.objects.create(
        image=image,
        size=size,
        storage_key=f"{image.storage_key}/{size}.webp",
        width=384,
        height=216,
        file_size=1024,
    )


def make_tombstone(storage_key: str, **kwargs: object) -> OrphanedStorageObject:
    return OrphanedStorageObject.objects.create(storage_key=storage_key, **kwargs)


def abandoned_upload(**kwargs: object) -> ProjectImage:
    """A `PENDING` row old enough that its presigned PUT has long expired."""
    image = ProjectImageFactory(upload_status=UploadStatus.PENDING, **kwargs)
    age_out(image)
    return image


def age_out(image: ProjectImage) -> None:
    """`created_at` is `auto_now_add`, so backdating needs a direct update."""
    stale = timezone.now() - timedelta(hours=PENDING_UPLOAD_MAX_AGE_HOURS + 1)
    ProjectImage.objects.filter(pk=image.pk).update(created_at=stale)


def recorded_keys() -> set[str]:
    return set(OrphanedStorageObject.objects.values_list("storage_key", flat=True))


def assert_no_tombstones_left() -> None:
    assert not OrphanedStorageObject.objects.exists()


# ----------------------------------------------------------------------
# Recording — the delete paths that lose keys without this
# ----------------------------------------------------------------------


@pytest.mark.django_db
class TestRecording:
    def test_deleting_an_article_records_every_image_key(self):
        article = ArticleFactory()
        keys = {article_image(article).storage_key for _ in range(3)}

        HANDLERS.articles.delete_article(article.id)

        assert recorded_keys() == keys

    def test_deleting_an_article_records_its_variant_keys_too(self):
        article = ArticleFactory()
        image = article_image(article)
        variant_keys = {
            make_variant(image, size).storage_key
            for size in (VariantSize.THUMB, VariantSize.MEDIUM)
        }

        HANDLERS.articles.delete_article(article.id)

        assert recorded_keys() == {image.storage_key, *variant_keys}

    def test_deleting_a_project_records_its_gallery_keys(self):
        # The second cascade, and the one option (a) — deleting through
        # `delete_image` inside `delete_article` — would never have covered.
        # No article here: `Article.channel` is PROTECT and `Channel` cascades
        # from `Project`, so a project with articles cannot be deleted at all.
        project = ProjectFactory()
        image = ProjectImageFactory(project=project)
        variant_key = make_variant(image).storage_key
        icon_key = ProjectImageFactory(project=project, is_icon=True).storage_key

        HANDLERS.project.delete(project.id, project.creator_id)

        assert recorded_keys() == {image.storage_key, variant_key, icon_key}

    def test_deleting_an_image_directly_records_its_key(self):
        image = ProjectImageFactory()

        with patch(DELETE_OBJECT):
            HANDLERS.images.delete_image(image)

        assert recorded_keys() == {image.storage_key}

    def test_recording_the_same_key_twice_does_not_raise(self):
        image = ProjectImageFactory()
        make_tombstone(image.storage_key)

        with patch(DELETE_OBJECT):
            HANDLERS.images.delete_image(image)

        assert recorded_keys() == {image.storage_key}


# ----------------------------------------------------------------------
# Draining
# ----------------------------------------------------------------------


@pytest.mark.django_db
class TestSweep:
    def test_sweep_deletes_the_object_and_clears_the_row(self, handler):
        make_tombstone("projects/images/x.jpg")

        with patch(DELETE_OBJECT) as delete_object:
            result = handler.sweep_orphaned_objects()

        delete_object.assert_called_once_with("projects/images/x.jpg")
        assert result.objects_deleted == 1
        assert_no_tombstones_left()

    def test_sweep_keeps_the_row_and_counts_the_attempt_on_failure(self, handler):
        row = make_tombstone("k")

        with patch(DELETE_OBJECT, side_effect=RuntimeError("boom")):
            result = handler.sweep_orphaned_objects()

        row.refresh_from_db()
        assert row.attempts == 1
        assert "boom" in row.last_error
        assert result.failures == 1
        assert result.objects_deleted == 0

    def test_sweep_stops_retrying_a_tombstone_past_the_attempt_ceiling(self, handler):
        make_tombstone("burnt", attempts=MAX_SWEEP_ATTEMPTS)

        with patch(DELETE_OBJECT) as delete_object:
            handler.sweep_orphaned_objects()

        delete_object.assert_not_called()
        assert OrphanedStorageObject.objects.filter(storage_key="burnt").exists()

    def test_sweep_drains_oldest_first_up_to_the_batch_size(self, handler):
        for n in range(3):
            row = make_tombstone(f"key-{n}")
            OrphanedStorageObject.objects.filter(pk=row.pk).update(
                created_at=timezone.now() - timedelta(hours=3 - n)
            )

        with patch(DELETE_OBJECT) as delete_object:
            handler.sweep_orphaned_objects(batch_size=2)

        assert [c.args[0] for c in delete_object.call_args_list] == ["key-0", "key-1"]
        assert recorded_keys() == {"key-2"}

    def test_a_failed_object_is_retried_by_the_next_sweep(self, handler):
        make_tombstone("flaky")

        with patch(DELETE_OBJECT, side_effect=RuntimeError("transient")):
            handler.sweep_orphaned_objects()
        with patch(DELETE_OBJECT) as delete_object:
            handler.sweep_orphaned_objects()

        delete_object.assert_called_once_with("flaky")
        assert_no_tombstones_left()


# ----------------------------------------------------------------------
# End to end — the article delete that motivated the finding
# ----------------------------------------------------------------------


@pytest.mark.django_db
class TestArticleDeleteEndToEnd:
    def test_deleting_an_article_then_sweeping_deletes_every_object(self, handler):
        article = ArticleFactory()
        images = [article_image(article) for _ in range(3)]
        expected = {image.storage_key for image in images}
        expected |= {make_variant(image).storage_key for image in images}

        HANDLERS.articles.delete_article(article.id)
        with patch(DELETE_OBJECT) as delete_object:
            result = handler.sweep_orphaned_objects()

        assert {c.args[0] for c in delete_object.call_args_list} == expected
        assert result.objects_deleted == len(expected)
        assert_no_tombstones_left()

    def test_a_storage_failure_leaves_the_key_recoverable(self, handler):
        """The property option (a) — deleting through S3 in the request — cannot
        have: the row is already gone, and the key survives the failure.
        """
        article = ArticleFactory()
        key = article_image(article).storage_key

        HANDLERS.articles.delete_article(article.id)
        with patch(DELETE_OBJECT, side_effect=RuntimeError("S3 down")):
            handler.sweep_orphaned_objects()

        assert recorded_keys() == {key}


# ----------------------------------------------------------------------
# Abandoned PENDING uploads (FOLLOW_UPS item 5)
# ----------------------------------------------------------------------


@pytest.mark.django_db
class TestAbandonedUploads:
    def test_sweep_deletes_stale_pending_rows_and_their_objects(self, handler):
        image = abandoned_upload()

        with patch(DELETE_OBJECT) as delete_object:
            result = handler.sweep_orphaned_objects()

        delete_object.assert_called_once_with(image.storage_key)
        assert result.pending_uploads_reaped == 1
        assert not ProjectImage.objects.filter(pk=image.pk).exists()
        assert_no_tombstones_left()

    def test_sweep_leaves_a_pending_upload_still_within_its_window(self, handler):
        image = ProjectImageFactory(upload_status=UploadStatus.PENDING)

        with patch(DELETE_OBJECT) as delete_object:
            result = handler.sweep_orphaned_objects()

        delete_object.assert_not_called()
        assert result.pending_uploads_reaped == 0
        assert ProjectImage.objects.filter(pk=image.pk).exists()

    def test_sweep_leaves_an_uploaded_image_alone_however_old(self, handler):
        image = ProjectImageFactory(upload_status=UploadStatus.UPLOADED)
        age_out(image)

        with patch(DELETE_OBJECT) as delete_object:
            handler.sweep_orphaned_objects()

        delete_object.assert_not_called()
        assert ProjectImage.objects.filter(pk=image.pk).exists()

    def test_sweep_leaves_a_failed_upload_for_its_own_decision(self, handler):
        image = ProjectImageFactory(upload_status=UploadStatus.FAILED)
        age_out(image)

        with patch(DELETE_OBJECT):
            handler.sweep_orphaned_objects()

        assert ProjectImage.objects.filter(pk=image.pk).exists()
