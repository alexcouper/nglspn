from __future__ import annotations

import io
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws
from PIL import Image

from apps.projects.models import ImageVariant, UploadStatus, VariantSize
from services.image.django_impl.handler import DjangoImageHandler
from tests.factories import ProjectImageFactory

TEST_BUCKET = "test-bucket"
TEST_REGION = "us-east-1"


def _create_test_image(width: int, height: int, fmt: str = "JPEG") -> bytes:
    """Create a test image of the given dimensions and return as bytes."""
    img = Image.new("RGB", (width, height), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def s3_client():
    with mock_aws():
        conn = boto3.client("s3", region_name=TEST_REGION)
        conn.create_bucket(Bucket=TEST_BUCKET)
        yield conn


@pytest.fixture
def mock_storage_settings(settings):
    settings.S3_BUCKET_NAME = TEST_BUCKET
    settings.S3_ENDPOINT_URL = "https://s3.us-east-1.amazonaws.com"
    settings.S3_REGION = TEST_REGION
    settings.S3_PUBLIC_URL_BASE = (
        f"https://{TEST_BUCKET}.s3.{TEST_REGION}.amazonaws.com"
    )
    settings.SCW_ACCESS_KEY = "test-access-key"
    settings.SCW_SECRET_KEY = "test-secret-key"  # noqa: S105


@pytest.fixture
def mock_storage(s3_client, mock_storage_settings):
    with mock_aws():
        s3_client.create_bucket(Bucket=TEST_BUCKET)
        with patch("services.storage.storage_service._client", s3_client):
            yield s3_client


@pytest.fixture
def handler():
    return DjangoImageHandler()


@pytest.mark.django_db
class TestGenerateVariants:
    def test_generates_all_three_variants_for_large_image(self, mock_storage, handler):
        image_bytes = _create_test_image(4000, 2250)
        mock_storage.put_object(
            Bucket=TEST_BUCKET,
            Key="projects/abc/def123/photo.jpg",
            Body=image_bytes,
        )

        image = ProjectImageFactory(
            storage_key="projects/abc/def123/photo.jpg",
            width=4000,
            height=2250,
            upload_status=UploadStatus.UPLOADED,
        )

        handler.generate_variants(str(image.id))

        variants = ImageVariant.objects.filter(image=image).order_by("width")
        assert variants.count() == 3

        thumb = variants.get(size=VariantSize.THUMB)
        assert thumb.width == 384
        assert thumb.storage_key == "projects/abc/def123/photo/thumb.webp"
        assert thumb.file_size > 0

        medium = variants.get(size=VariantSize.MEDIUM)
        assert medium.width == 768
        assert medium.storage_key == "projects/abc/def123/photo/medium.webp"

        large = variants.get(size=VariantSize.LARGE)
        assert large.width == 1536
        assert large.storage_key == "projects/abc/def123/photo/large.webp"

    def test_skips_sizes_larger_than_original(self, mock_storage, handler):
        image_bytes = _create_test_image(500, 300)
        mock_storage.put_object(
            Bucket=TEST_BUCKET,
            Key="projects/abc/def123/photo.jpg",
            Body=image_bytes,
        )

        image = ProjectImageFactory(
            storage_key="projects/abc/def123/photo.jpg",
            width=500,
            height=300,
            upload_status=UploadStatus.UPLOADED,
        )

        handler.generate_variants(str(image.id))

        variants = ImageVariant.objects.filter(image=image)
        assert variants.count() == 1
        assert variants.first().size == VariantSize.THUMB

    def test_no_variants_for_tiny_image(self, mock_storage, handler):
        image_bytes = _create_test_image(200, 150)
        mock_storage.put_object(
            Bucket=TEST_BUCKET,
            Key="projects/abc/def123/tiny.png",
            Body=image_bytes,
        )

        image = ProjectImageFactory(
            storage_key="projects/abc/def123/tiny.png",
            width=200,
            height=150,
            upload_status=UploadStatus.UPLOADED,
        )

        handler.generate_variants(str(image.id))

        assert ImageVariant.objects.filter(image=image).count() == 0

    def test_partial_failure_preserves_completed_variants(self, mock_storage, handler):
        image_bytes = _create_test_image(4000, 2250)
        mock_storage.put_object(
            Bucket=TEST_BUCKET,
            Key="projects/abc/def123/photo.jpg",
            Body=image_bytes,
        )

        image = ProjectImageFactory(
            storage_key="projects/abc/def123/photo.jpg",
            width=4000,
            height=2250,
            upload_status=UploadStatus.UPLOADED,
        )

        # Make upload_object fail after the first variant
        call_count = 0
        original_upload = handler._generate_single_variant.__func__  # noqa: SLF001

        msg = "Simulated S3 failure"

        def flaky_generate(
            self_inner,
            img,
            img_model,
            base_key,
            size,
            target_width,
        ):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise OSError(msg)
            return original_upload(
                self_inner,
                img,
                img_model,
                base_key,
                size,
                target_width,
            )

        with patch.object(type(handler), "_generate_single_variant", flaky_generate):
            handler.generate_variants(str(image.id))

        # First variant should be preserved, second failed, third should succeed
        variants = ImageVariant.objects.filter(image=image)
        assert variants.count() == 2
        sizes = set(variants.values_list("size", flat=True))
        assert VariantSize.THUMB in sizes
        assert VariantSize.LARGE in sizes

    def test_skips_pending_image(self, handler):
        image = ProjectImageFactory(
            width=4000,
            height=2250,
            upload_status=UploadStatus.PENDING,
        )

        handler.generate_variants(str(image.id))

        assert ImageVariant.objects.filter(image=image).count() == 0

    def test_backfills_dimensions_when_width_missing(self, mock_storage, handler):
        image_bytes = _create_test_image(4000, 2250)
        mock_storage.put_object(
            Bucket=TEST_BUCKET,
            Key="projects/abc/def123/photo.jpg",
            Body=image_bytes,
        )

        image = ProjectImageFactory(
            storage_key="projects/abc/def123/photo.jpg",
            width=None,
            height=None,
            upload_status=UploadStatus.UPLOADED,
        )

        handler.generate_variants(str(image.id))

        image.refresh_from_db()
        assert image.width == 4000
        assert image.height == 2250

        variants = ImageVariant.objects.filter(image=image).order_by("width")
        assert variants.count() == 3

    def test_idempotent_skips_existing_variants(self, mock_storage, handler):
        image_bytes = _create_test_image(4000, 2250)
        mock_storage.put_object(
            Bucket=TEST_BUCKET,
            Key="projects/abc/def123/photo.jpg",
            Body=image_bytes,
        )

        image = ProjectImageFactory(
            storage_key="projects/abc/def123/photo.jpg",
            width=4000,
            height=2250,
            upload_status=UploadStatus.UPLOADED,
        )

        handler.generate_variants(str(image.id))
        assert ImageVariant.objects.filter(image=image).count() == 3

        # Running again should not create duplicates
        handler.generate_variants(str(image.id))
        assert ImageVariant.objects.filter(image=image).count() == 3
