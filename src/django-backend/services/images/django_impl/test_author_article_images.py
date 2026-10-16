"""Images of an author-owned article: no project, stored under the article."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.projects.models import Image, OrphanedStorageObject, UploadStatus
from services.images.django_impl.handler import DjangoImageHandler
from services.images.handler_interface import (
    PENDING_UPLOAD_MAX_AGE_HOURS,
    FileMeta,
)
from tests.factories import ArticleFactory, AuthorArticleFactory, article_image

PRESIGN = "services.storage.storage_service.generate_presigned_upload_url"
OBJECT_EXISTS = "services.storage.storage_service.object_exists"
DELETE_OBJECT = "services.storage.storage_service.delete_object"
VARIANTS_TASK = "api.tasks.images.generate_image_variants"


@pytest.fixture
def handler():
    return DjangoImageHandler()


def a_file(name: str = "figure.png") -> FileMeta:
    return FileMeta(filename=name, content_type="image/png", file_size=1024)


def reserve(handler, article) -> Image:
    with patch(PRESIGN) as presign:
        presign.return_value = {"upload_url": "u", "method": "PUT", "headers": {}}
        return handler.create_article_upload(article, a_file()).image


def complete(handler, image) -> Image:
    with patch(OBJECT_EXISTS, return_value=True), patch(VARIANTS_TASK) as task:
        completed = handler.complete_upload(image, width=800, height=600)
    task.enqueue.assert_called_once_with(str(image.id))
    return completed


@pytest.mark.django_db
class TestReservingAgainstAnAuthorOwnedArticle:
    def test_row_belongs_to_the_article_alone(self, handler):
        article = AuthorArticleFactory()

        image = reserve(handler, article)

        assert image.article_id == article.id
        assert image.project_id is None

    def test_key_lives_under_the_article(self, handler):
        article = AuthorArticleFactory()

        image = reserve(handler, article)

        assert image.storage_key.startswith(f"articles/{article.id}/")
        assert image.storage_key.endswith("/figure.png")

    def test_a_project_articles_key_still_lives_under_the_project(self, handler):
        article = ArticleFactory()

        image = reserve(handler, article)

        assert image.storage_key.startswith(f"projects/{article.project_id}/")


@pytest.mark.django_db
class TestCompletingAndDeleting:
    def test_completion_marks_uploaded_and_queues_variants(self, handler):
        image = reserve(handler, AuthorArticleFactory())

        completed = complete(handler, image)

        assert completed.upload_status == UploadStatus.UPLOADED
        assert (completed.width, completed.height) == (800, 600)
        assert completed.is_main is False

    def test_delete_removes_the_row_and_tombstones_the_key(self, handler):
        image = article_image(AuthorArticleFactory())

        with patch(DELETE_OBJECT) as delete_object:
            handler.delete_image(image)

        delete_object.assert_called_once_with(image.storage_key)
        assert not Image.objects.filter(pk=image.pk).exists()
        assert OrphanedStorageObject.objects.filter(
            storage_key=image.storage_key
        ).exists()

    def test_deleting_the_article_tombstones_both_images(self, handler):
        article = AuthorArticleFactory()
        keys = {article_image(article).storage_key for _ in range(2)}

        article.delete()

        assert not Image.objects.filter(article_id=article.id).exists()
        assert (
            set(OrphanedStorageObject.objects.values_list("storage_key", flat=True))
            >= keys
        )


@pytest.mark.django_db
class TestSweep:
    def test_an_abandoned_reservation_is_reaped_like_a_project_one(self, handler):
        image = reserve(handler, AuthorArticleFactory())
        Image.objects.filter(pk=image.pk).update(
            created_at=timezone.now()
            - timedelta(hours=PENDING_UPLOAD_MAX_AGE_HOURS + 1)
        )

        with patch(DELETE_OBJECT) as delete_object:
            result = handler.sweep_orphaned_objects()

        assert result.pending_uploads_reaped == 1
        delete_object.assert_called_once_with(image.storage_key)
        assert not Image.objects.filter(pk=image.pk).exists()
