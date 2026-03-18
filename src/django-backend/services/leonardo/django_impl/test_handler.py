from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.projects.models import (
    ApprovalStatus,
    GenerationStatus,
    ImagePurpose,
    ProjectImage,
    UploadStatus,
)
from services.leonardo.django_impl.client import GeneratedImage, GenerationResult
from services.leonardo.django_impl.handler import DjangoLeonardoHandler
from tests.factories import ImageGenerationRequestFactory, ProjectImageFactory


@pytest.fixture
def handler():
    handler = DjangoLeonardoHandler()
    handler._client = MagicMock()
    return handler


@pytest.mark.django_db
class TestGenerate:
    def test_successful_icon_generation(self, handler):
        request = ImageGenerationRequestFactory(
            purpose=ImagePurpose.ICON,
            num_variants=2,
        )

        handler._client.create_generation.return_value = "gen-123"
        handler._client.poll_until_complete.return_value = GenerationResult(
            generation_id="gen-123",
            status="COMPLETE",
            images=[
                GeneratedImage(
                    url="https://cdn.leonardo.ai/img1.png", leonardo_id="i1"
                ),
                GeneratedImage(
                    url="https://cdn.leonardo.ai/img2.png", leonardo_id="i2"
                ),
            ],
        )
        handler._client.download_image.return_value = b"fake-image-bytes"

        with patch(
            "services.leonardo.django_impl.handler.storage_service"
        ) as mock_storage:
            mock_storage.generate_upload_key.return_value = "projects/test/gen.png"
            with patch(
                "services.leonardo.django_impl.handler.generate_image_variants"
            ) as mock_variants:
                mock_variants.enqueue = MagicMock()
                handler.generate(str(request.id))

        request.refresh_from_db()
        assert request.status == GenerationStatus.COMPLETED
        assert request.leonardo_generation_id == "gen-123"
        assert request.completed_at is not None

        images = ProjectImage.objects.filter(
            project=request.project,
            purpose=ImagePurpose.ICON,
            approval_status=ApprovalStatus.PROPOSED,
        )
        assert images.count() == 2

    def test_failed_generation_sets_error(self, handler):
        request = ImageGenerationRequestFactory()

        handler._client.create_generation.return_value = "gen-456"
        handler._client.poll_until_complete.return_value = GenerationResult(
            generation_id="gen-456",
            status="FAILED",
            images=[],
        )

        handler.generate(str(request.id))

        request.refresh_from_db()
        assert request.status == GenerationStatus.FAILED
        assert "FAILED" in request.error_message

    def test_timeout_sets_error(self, handler):
        request = ImageGenerationRequestFactory()

        handler._client.create_generation.return_value = "gen-789"
        handler._client.poll_until_complete.return_value = GenerationResult(
            generation_id="gen-789",
            status="TIMEOUT",
            images=[],
        )

        handler.generate(str(request.id))

        request.refresh_from_db()
        assert request.status == GenerationStatus.FAILED
        assert "timed out" in request.error_message

    def test_replaces_old_proposed_images(self, handler):
        request = ImageGenerationRequestFactory(purpose=ImagePurpose.ICON)

        # Create existing proposed images
        old_proposed = ProjectImageFactory(
            project=request.project,
            purpose=ImagePurpose.ICON,
            approval_status=ApprovalStatus.PROPOSED,
            upload_status=UploadStatus.UPLOADED,
        )
        old_id = old_proposed.id

        handler._client.create_generation.return_value = "gen-new"
        handler._client.poll_until_complete.return_value = GenerationResult(
            generation_id="gen-new",
            status="COMPLETE",
            images=[
                GeneratedImage(url="https://cdn.leonardo.ai/new.png", leonardo_id="n1"),
            ],
        )
        handler._client.download_image.return_value = b"new-image-bytes"

        with patch(
            "services.leonardo.django_impl.handler.storage_service"
        ) as mock_storage:
            mock_storage.generate_upload_key.return_value = "projects/test/new.png"
            with patch(
                "services.leonardo.django_impl.handler.generate_image_variants"
            ) as mock_variants:
                mock_variants.enqueue = MagicMock()
                handler.generate(str(request.id))

        assert not ProjectImage.objects.filter(id=old_id).exists()

        new_images = ProjectImage.objects.filter(
            project=request.project,
            purpose=ImagePurpose.ICON,
            approval_status=ApprovalStatus.PROPOSED,
        )
        assert new_images.count() == 1

    def test_uploads_reference_image_for_context(self, handler):
        ref_image = ProjectImageFactory(upload_status=UploadStatus.UPLOADED)
        request = ImageGenerationRequestFactory(
            purpose=ImagePurpose.MAIN_IMAGE,
            reference_image=ref_image,
        )

        handler._client.upload_init_image.return_value = "leo-ref-123"
        handler._client.create_generation.return_value = "gen-ref"
        handler._client.poll_until_complete.return_value = GenerationResult(
            generation_id="gen-ref",
            status="COMPLETE",
            images=[
                GeneratedImage(url="https://cdn.leonardo.ai/ref.png", leonardo_id="r1"),
            ],
        )
        handler._client.download_image.return_value = b"ref-image-bytes"

        with patch(
            "services.leonardo.django_impl.handler.storage_service"
        ) as mock_storage:
            mock_storage.download_object.return_value = b"original-ref-bytes"
            mock_storage.generate_upload_key.return_value = "projects/test/ref.png"
            with patch(
                "services.leonardo.django_impl.handler.generate_image_variants"
            ) as mock_variants:
                mock_variants.enqueue = MagicMock()
                handler.generate(str(request.id))

        handler._client.upload_init_image.assert_called_once()
        create_call = handler._client.create_generation.call_args
        assert create_call.kwargs["context_image_id"] == "leo-ref-123"

    def test_nonexistent_request_does_nothing(self, handler):
        handler.generate("00000000-0000-0000-0000-000000000000")
        handler._client.create_generation.assert_not_called()

    def test_exception_during_generation_sets_failed(self, handler):
        request = ImageGenerationRequestFactory()

        handler._client.create_generation.side_effect = RuntimeError("API down")

        handler.generate(str(request.id))

        request.refresh_from_db()
        assert request.status == GenerationStatus.FAILED
