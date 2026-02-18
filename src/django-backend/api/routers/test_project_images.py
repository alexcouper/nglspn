"""Tests for project image upload functionality."""

import json
from unittest.mock import patch

import boto3
import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    is_,
)
from moto import mock_aws

from apps.projects.models import ProjectImage, UploadStatus
from tests.factories import ProjectFactory

# Test bucket configuration
TEST_BUCKET = "test-bucket"
TEST_REGION = "us-east-1"


@pytest.fixture
def s3_client():
    """Create mocked S3 client and bucket."""
    with mock_aws():
        conn = boto3.client("s3", region_name=TEST_REGION)
        conn.create_bucket(Bucket=TEST_BUCKET)
        yield conn


@pytest.fixture
def mock_storage_settings(settings):
    """Configure settings for test S3 bucket."""
    settings.S3_BUCKET_NAME = TEST_BUCKET
    settings.S3_ENDPOINT_URL = "https://s3.us-east-1.amazonaws.com"
    settings.S3_REGION = TEST_REGION
    settings.S3_PUBLIC_URL_BASE = (
        f"https://{TEST_BUCKET}.s3.{TEST_REGION}.amazonaws.com"
    )
    settings.SCW_ACCESS_KEY = "test-access-key"
    settings.SCW_SECRET_KEY = "test-secret-key"  # noqa: S105


@pytest.fixture
def mock_storage_service(s3_client, mock_storage_settings):
    """Mock the storage service to use moto."""
    with mock_aws():
        # Create bucket inside the mock context
        s3_client.create_bucket(Bucket=TEST_BUCKET)

        # Patch the storage service client
        with patch(
            "services.storage.storage_service._client",
            s3_client,
        ):
            yield s3_client


class TestGetUploadUrl:
    def test_generates_presigned_url(
        self,
        client,
        project,
        auth_headers,
        mock_storage_service,
    ) -> None:
        payload = {
            "filename": "screenshot.png",
            "content_type": "image/png",
            "file_size": 1024,
        }

        response = client.post(
            f"/api/my/projects/{project.id}/images/upload-url",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        data = response.json()
        assert_that(data, has_entries(upload_url=contains_string("http")))
        assert_that(data, has_entries(method="PUT"))
        assert_that(data, has_entries(image_id=is_(str)))
        assert_that(data, has_entries(storage_key=contains_string(str(project.id))))

    def test_rejects_invalid_content_type(
        self,
        client,
        project,
        auth_headers,
    ) -> None:
        payload = {
            "filename": "file.exe",
            "content_type": "application/octet-stream",
            "file_size": 1024,
        }

        response = client.post(
            f"/api/my/projects/{project.id}/images/upload-url",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("Content type"))

    def test_rejects_file_too_large(
        self,
        client,
        project,
        auth_headers,
    ) -> None:
        payload = {
            "filename": "huge.png",
            "content_type": "image/png",
            "file_size": 100 * 1024 * 1024,  # 100MB
        }

        response = client.post(
            f"/api/my/projects/{project.id}/images/upload-url",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("10MB"))

    def test_rejects_when_max_images_reached(
        self,
        client,
        user,
        auth_headers,
        mock_storage_service,
    ) -> None:
        project = ProjectFactory(owner=user)
        # Create 10 uploaded images
        for i in range(10):
            ProjectImage.objects.create(
                project=project,
                storage_key=f"test/key{i}.png",
                original_filename=f"image{i}.png",
                content_type="image/png",
                file_size=1024,
                upload_status=UploadStatus.UPLOADED,
                display_order=i,
            )

        payload = {
            "filename": "one_more.png",
            "content_type": "image/png",
            "file_size": 1024,
        }

        response = client.post(
            f"/api/my/projects/{project.id}/images/upload-url",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("Maximum"))

    def test_requires_authentication(self, client, project) -> None:
        payload = {
            "filename": "screenshot.png",
            "content_type": "image/png",
            "file_size": 1024,
        }

        response = client.post(
            f"/api/my/projects/{project.id}/images/upload-url",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))


class TestCompleteUpload:
    def test_marks_upload_complete(
        self,
        client,
        project,
        auth_headers,
        mock_storage_service,
    ) -> None:
        # Create pending image
        image = ProjectImage.objects.create(
            project=project,
            storage_key="test/key.png",
            original_filename="test.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.PENDING,
        )

        # Simulate file existing in S3
        mock_storage_service.put_object(
            Bucket=TEST_BUCKET,
            Key="test/key.png",
            Body=b"test",
        )

        response = client.post(
            f"/api/my/projects/{project.id}/images/{image.id}/complete",
            data=json.dumps({"width": 800, "height": 600}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        image.refresh_from_db()
        assert_that(image.upload_status, equal_to(UploadStatus.UPLOADED))
        assert_that(image.width, equal_to(800))
        assert_that(image.height, equal_to(600))

    def test_first_image_becomes_main(
        self,
        client,
        project,
        auth_headers,
        mock_storage_service,
    ) -> None:
        image = ProjectImage.objects.create(
            project=project,
            storage_key="test/first.png",
            original_filename="first.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.PENDING,
        )

        mock_storage_service.put_object(
            Bucket=TEST_BUCKET,
            Key="test/first.png",
            Body=b"test",
        )

        response = client.post(
            f"/api/my/projects/{project.id}/images/{image.id}/complete",
            data=json.dumps({}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        image.refresh_from_db()
        assert_that(image.is_main, is_(True))

    def test_fails_if_file_not_in_storage(
        self,
        client,
        project,
        auth_headers,
        mock_storage_service,
    ) -> None:
        image = ProjectImage.objects.create(
            project=project,
            storage_key="test/missing.png",
            original_filename="missing.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.PENDING,
        )

        response = client.post(
            f"/api/my/projects/{project.id}/images/{image.id}/complete",
            data=json.dumps({}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["detail"], contains_string("not found in storage"))


class TestDeleteImage:
    def test_deletes_image(
        self,
        client,
        project,
        auth_headers,
        mock_storage_service,
    ) -> None:
        image = ProjectImage.objects.create(
            project=project,
            storage_key="test/delete-me.png",
            original_filename="delete-me.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
        )

        mock_storage_service.put_object(
            Bucket=TEST_BUCKET,
            Key="test/delete-me.png",
            Body=b"test",
        )

        response = client.delete(
            f"/api/my/projects/{project.id}/images/{image.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(204))
        assert_that(ProjectImage.objects.filter(id=image.id).exists(), is_(False))

    def test_promotes_next_image_to_main_when_main_deleted(
        self,
        client,
        project,
        auth_headers,
        mock_storage_service,
    ) -> None:
        main_image = ProjectImage.objects.create(
            project=project,
            storage_key="test/main.png",
            original_filename="main.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
            is_main=True,
            display_order=0,
        )
        second_image = ProjectImage.objects.create(
            project=project,
            storage_key="test/second.png",
            original_filename="second.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
            is_main=False,
            display_order=1,
        )

        mock_storage_service.put_object(
            Bucket=TEST_BUCKET,
            Key="test/main.png",
            Body=b"test",
        )

        response = client.delete(
            f"/api/my/projects/{project.id}/images/{main_image.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(204))
        second_image.refresh_from_db()
        assert_that(second_image.is_main, is_(True))


class TestSetMainImage:
    def test_sets_main_image(
        self,
        client,
        project,
        auth_headers,
    ) -> None:
        image1 = ProjectImage.objects.create(
            project=project,
            storage_key="test/img1.png",
            original_filename="img1.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
            is_main=True,
        )
        image2 = ProjectImage.objects.create(
            project=project,
            storage_key="test/img2.png",
            original_filename="img2.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
            is_main=False,
        )

        response = client.post(
            f"/api/my/projects/{project.id}/images/main",
            data=json.dumps({"image_id": str(image2.id)}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        image1.refresh_from_db()
        image2.refresh_from_db()
        assert_that(image1.is_main, is_(False))
        assert_that(image2.is_main, is_(True))


class TestImageAuthorization:
    def test_cannot_upload_to_other_users_project(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        payload = {
            "filename": "screenshot.png",
            "content_type": "image/png",
            "file_size": 1024,
        }

        response = client.post(
            f"/api/my/projects/{other_project.id}/images/upload-url",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_cannot_delete_other_users_image(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        image = ProjectImage.objects.create(
            project=other_project,
            storage_key="test/other.png",
            original_filename="other.png",
            content_type="image/png",
            file_size=1024,
            upload_status=UploadStatus.UPLOADED,
        )

        response = client.delete(
            f"/api/my/projects/{other_project.id}/images/{image.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))
        assert_that(ProjectImage.objects.filter(id=image.id).exists(), is_(True))
