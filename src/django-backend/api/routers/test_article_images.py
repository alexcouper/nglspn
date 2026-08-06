"""Article images are addressed under the article that owns them.

The rows are still `ProjectImage` — same storage, same variant pipeline — but
the article is in the path, so there is no `source` / `source_id` pair that
could name a different article than the one the row is stored against.
"""

import json
from unittest.mock import patch

import boto3
import pytest
from hamcrest import assert_that, contains_string, equal_to, is_, is_not
from moto import mock_aws

from apps.projects.models import ProjectImage, UploadStatus
from services.images.handler_interface import MAX_IMAGES_PER_ARTICLE
from tests.factories import ArticleFactory, ProjectFactory, article_image

TEST_BUCKET = "test-bucket"
TEST_REGION = "us-east-1"


@pytest.fixture
def s3_client():
    with mock_aws():
        conn = boto3.client("s3", region_name=TEST_REGION)
        conn.create_bucket(Bucket=TEST_BUCKET)
        yield conn


@pytest.fixture
def mock_storage_service(s3_client, settings):
    settings.S3_BUCKET_NAME = TEST_BUCKET
    settings.S3_ENDPOINT_URL = "https://s3.us-east-1.amazonaws.com"
    settings.S3_REGION = TEST_REGION
    settings.S3_PUBLIC_URL_BASE = (
        f"https://{TEST_BUCKET}.s3.{TEST_REGION}.amazonaws.com"
    )
    settings.SCW_ACCESS_KEY = "test-access-key"
    settings.SCW_SECRET_KEY = "test-secret-key"  # noqa: S105
    with mock_aws():
        s3_client.create_bucket(Bucket=TEST_BUCKET)
        with patch("services.storage.storage_service._client", s3_client):
            yield s3_client


@pytest.fixture
def article(project):
    return ArticleFactory(project=project)


def images_url(article) -> str:
    return f"/api/projects/{article.project_id}/articles/{article.id}/images"


def request_upload_url(client, article, auth_headers, **overrides):
    payload = {
        "filename": "figure.png",
        "content_type": "image/png",
        "file_size": 1024,
    } | overrides
    return client.post(
        f"{images_url(article)}/upload-url",
        data=json.dumps(payload),
        content_type="application/json",
        **auth_headers,
    )


def complete_upload(client, article, image, auth_headers, storage, **dimensions):
    storage.put_object(Bucket=TEST_BUCKET, Key=image.storage_key, Body=b"test")
    with patch("api.tasks.images.generate_image_variants"):
        return client.post(
            f"{images_url(article)}/{image.id}/complete",
            data=json.dumps({"width": 800, "height": 600} | dimensions),
            content_type="application/json",
            **auth_headers,
        )


def make_pending_image(article, **overrides) -> ProjectImage:
    return ProjectImage.objects.create(
        project=article.project,
        article=article,
        storage_key="test/pending.png",
        original_filename="pending.png",
        content_type="image/png",
        file_size=1024,
        upload_status=UploadStatus.PENDING,
        **overrides,
    )


class TestGetUploadUrl:
    def test_reserves_a_row_linked_to_the_article(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        response = request_upload_url(client, article, auth_headers)

        assert_that(response.status_code, equal_to(200))
        image = ProjectImage.objects.get(id=response.json()["image_id"])
        assert_that(image.article_id, equal_to(article.id))
        assert_that(image.project_id, equal_to(article.project_id))
        assert_that(image.upload_status, equal_to(UploadStatus.PENDING))

    def test_returns_a_presigned_put(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        response = request_upload_url(client, article, auth_headers)

        body = response.json()
        assert_that(body["method"], equal_to("PUT"))
        assert_that(body["upload_url"], contains_string(TEST_BUCKET))
        assert_that(body["storage_key"], is_not(equal_to("")))

    def test_rejects_an_unsupported_content_type(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        response = request_upload_url(
            client, article, auth_headers, content_type="application/pdf"
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("Content type"))

    def test_rejects_an_oversized_file(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        response = request_upload_url(
            client, article, auth_headers, file_size=11 * 1024 * 1024
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("File size"))

    def test_rejects_an_article_on_another_project(
        self, client, project, auth_headers, mock_storage_service
    ) -> None:
        foreign = ArticleFactory()

        response = client.post(
            f"/api/projects/{project.id}/articles/{foreign.id}/images/upload-url",
            data=json.dumps(
                {
                    "filename": "figure.png",
                    "content_type": "image/png",
                    "file_size": 1024,
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_rejects_a_user_without_edit_rights(
        self, client, other_auth_headers, article, mock_storage_service
    ) -> None:
        response = request_upload_url(client, article, other_auth_headers)

        assert_that(response.status_code, is_(equal_to(403)))

    def test_requires_authentication(
        self, client, article, mock_storage_service
    ) -> None:
        response = request_upload_url(client, article, {})

        assert_that(response.status_code, equal_to(401))


class TestArticleImageCap:
    def test_allows_an_upload_below_the_cap(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        for _ in range(MAX_IMAGES_PER_ARTICLE - 1):
            article_image(article)

        response = request_upload_url(client, article, auth_headers)

        assert_that(response.status_code, equal_to(200))

    def test_rejects_an_upload_at_the_cap(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        for _ in range(MAX_IMAGES_PER_ARTICLE):
            article_image(article)

        response = request_upload_url(client, article, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("per article"))

    def test_another_articles_images_do_not_count(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        sibling = ArticleFactory(project=article.project)
        for _ in range(MAX_IMAGES_PER_ARTICLE):
            article_image(sibling)

        response = request_upload_url(client, article, auth_headers)

        assert_that(response.status_code, equal_to(200))

    def test_abandoned_pending_rows_do_not_burn_a_slot(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        for _ in range(MAX_IMAGES_PER_ARTICLE):
            make_pending_image(article)

        response = request_upload_url(client, article, auth_headers)

        assert_that(response.status_code, equal_to(200))


class TestCompleteUpload:
    def test_marks_the_row_uploaded_with_its_dimensions(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        image = make_pending_image(article)

        response = complete_upload(
            client, article, image, auth_headers, mock_storage_service
        )

        assert_that(response.status_code, equal_to(200))
        image.refresh_from_db()
        assert_that(image.upload_status, equal_to(UploadStatus.UPLOADED))
        assert_that(image.width, equal_to(800))
        assert_that(image.height, equal_to(600))

    def test_never_promotes_the_article_image_to_the_project_cover(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        image = make_pending_image(article)

        complete_upload(client, article, image, auth_headers, mock_storage_service)

        image.refresh_from_db()
        assert_that(image.is_main, is_(False))

    def test_enqueues_variant_generation(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        image = make_pending_image(article)
        mock_storage_service.put_object(
            Bucket=TEST_BUCKET, Key=image.storage_key, Body=b"test"
        )

        with patch("api.tasks.images.generate_image_variants") as mock_task:
            client.post(
                f"{images_url(article)}/{image.id}/complete",
                data=json.dumps({"width": 800, "height": 600}),
                content_type="application/json",
                **auth_headers,
            )

        mock_task.enqueue.assert_called_once_with(str(image.id))

    def test_rejects_an_upload_that_never_landed_in_storage(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        image = make_pending_image(article)

        with patch("api.tasks.images.generate_image_variants"):
            response = client.post(
                f"{images_url(article)}/{image.id}/complete",
                data=json.dumps({"width": 800, "height": 600}),
                content_type="application/json",
                **auth_headers,
            )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("storage"))
        image.refresh_from_db()
        assert_that(image.upload_status, equal_to(UploadStatus.PENDING))

    def test_rejects_an_image_belonging_to_another_article(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        sibling = ArticleFactory(project=article.project)
        image = make_pending_image(sibling)

        response = complete_upload(
            client, article, image, auth_headers, mock_storage_service
        )

        assert_that(response.status_code, equal_to(404))

    def test_rejects_a_project_gallery_image(
        self, client, project, article, auth_headers, mock_storage_service
    ) -> None:
        gallery = ProjectImage.objects.create(
            project=project,
            storage_key="test/gallery.png",
            original_filename="gallery.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.PENDING,
        )

        response = complete_upload(
            client, article, gallery, auth_headers, mock_storage_service
        )

        assert_that(response.status_code, equal_to(404))


class TestDeleteImage:
    def test_removes_the_row(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        image = article_image(article)

        response = client.delete(f"{images_url(article)}/{image.id}", **auth_headers)

        assert_that(response.status_code, equal_to(204))
        assert_that(ProjectImage.objects.filter(id=image.id).exists(), is_(False))

    def test_removes_a_pending_row_the_wizard_abandoned(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        image = make_pending_image(article)

        response = client.delete(f"{images_url(article)}/{image.id}", **auth_headers)

        assert_that(response.status_code, equal_to(204))
        assert_that(ProjectImage.objects.filter(id=image.id).exists(), is_(False))

    def test_leaves_a_project_gallery_image_alone(
        self, client, project, article, auth_headers, mock_storage_service
    ) -> None:
        gallery = ProjectImage.objects.create(
            project=project,
            storage_key="test/gallery.png",
            original_filename="gallery.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
        )

        response = client.delete(f"{images_url(article)}/{gallery.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))
        assert_that(ProjectImage.objects.filter(id=gallery.id).exists(), is_(True))

    def test_rejects_a_user_without_edit_rights(
        self, client, other_auth_headers, article, mock_storage_service
    ) -> None:
        image = article_image(article)

        response = client.delete(
            f"{images_url(article)}/{image.id}", **other_auth_headers
        )

        assert_that(response.status_code, equal_to(403))
        assert_that(ProjectImage.objects.filter(id=image.id).exists(), is_(True))


class TestArticleResponseImages:
    def test_lists_only_completed_uploads(
        self, client, article, auth_headers, mock_storage_service
    ) -> None:
        uploaded = article_image(article)
        make_pending_image(article)

        response = client.get(
            f"/api/projects/{article.project_id}/articles/{article.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        listed = [image["id"] for image in response.json()["images"]]
        assert_that(listed, equal_to([str(uploaded.id)]))


class TestAddressingByProjectSlug:
    def test_uploads_resolve_the_project_by_slug(
        self, client, user, auth_headers, mock_storage_service
    ) -> None:
        project = ProjectFactory(owner=user, slug="a-project")
        article = ArticleFactory(project=project)

        response = client.post(
            f"/api/projects/{project.slug}/articles/{article.id}/images/upload-url",
            data=json.dumps(
                {
                    "filename": "figure.png",
                    "content_type": "image/png",
                    "file_size": 1024,
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        image = ProjectImage.objects.get(id=response.json()["image_id"])
        assert_that(image.article_id, equal_to(article.id))
