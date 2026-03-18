from __future__ import annotations

import logging
import uuid

from django.utils import timezone

from api.tasks.images import generate_image_variants
from apps.projects.models import (
    ApprovalStatus,
    GenerationStatus,
    ImageGenerationRequest,
    ImagePurpose,
    ProjectImage,
    UploadStatus,
)
from services.leonardo.django_impl.client import (
    FLUX_KONTEXT_MODEL_ID,
    LeonardoAPIClient,
)
from services.leonardo.handler_interface import LeonardoHandlerInterface
from services.storage import storage_service

logger = logging.getLogger(__name__)


class DjangoLeonardoHandler(LeonardoHandlerInterface):
    def __init__(self) -> None:
        self._client = LeonardoAPIClient()

    def generate(self, generation_request_id: str) -> None:
        try:
            request = ImageGenerationRequest.objects.select_related(
                "project", "reference_image"
            ).get(id=generation_request_id)
        except ImageGenerationRequest.DoesNotExist:
            logger.warning(
                "Generation request %s not found", generation_request_id
            )
            return

        request.status = GenerationStatus.GENERATING
        request.save(update_fields=["status"])

        try:
            self._execute_generation(request)
        except Exception:
            logger.exception(
                "Generation failed for request %s", generation_request_id
            )
            request.status = GenerationStatus.FAILED
            request.error_message = "Unexpected error during generation"
            request.save(update_fields=["status", "error_message"])

    def _execute_generation(self, request: ImageGenerationRequest) -> None:
        # Upload reference image if needed
        context_image_id = None
        if request.reference_image:
            ref_bytes = storage_service.download_object(
                request.reference_image.storage_key
            )
            extension = _get_extension(request.reference_image.content_type)
            context_image_id = self._client.upload_init_image(ref_bytes, extension)

        # Determine preset style
        preset_style = _get_preset_style(request.purpose)

        # Create the generation
        generation_id = self._client.create_generation(
            prompt=request.prompt_text,
            model_id=request.leonardo_model_id,
            width=request.width,
            height=request.height,
            num_images=request.num_variants,
            preset_style=preset_style,
            alchemy=request.leonardo_model_id != FLUX_KONTEXT_MODEL_ID,
            context_image_id=context_image_id,
        )

        request.leonardo_generation_id = generation_id
        request.save(update_fields=["leonardo_generation_id"])

        # Poll until complete
        result = self._client.poll_until_complete(generation_id)

        if result.status == "COMPLETE":
            self._save_generated_images(request, result)
            request.status = GenerationStatus.COMPLETED
            request.completed_at = timezone.now()
            request.save(update_fields=["status", "completed_at"])
        elif result.status == "TIMEOUT":
            request.status = GenerationStatus.FAILED
            request.error_message = "Generation timed out"
            request.save(update_fields=["status", "error_message"])
        else:
            request.status = GenerationStatus.FAILED
            request.error_message = f"Leonardo returned status: {result.status}"
            request.save(update_fields=["status", "error_message"])

    def _save_generated_images(self, request, result) -> None:
        # Delete previous proposed images for this project+purpose
        old_proposed = ProjectImage.objects.filter(
            project=request.project,
            purpose=request.purpose,
            approval_status=ApprovalStatus.PROPOSED,
        )
        for img in old_proposed:
            _delete_image_files(img)
        old_proposed.delete()

        # Download and save each generated image
        for gen_image in result.images:
            try:
                image_bytes = self._client.download_image(gen_image.url)
                storage_key = storage_service.generate_upload_key(
                    str(request.project.id),
                    f"generated-{uuid.uuid4().hex[:8]}.png",
                )
                storage_service.upload_object(
                    storage_key, image_bytes, "image/png"
                )

                project_image = ProjectImage.objects.create(
                    project=request.project,
                    storage_key=storage_key,
                    original_filename=f"generated-{request.purpose}.png",
                    content_type="image/png",
                    file_size=len(image_bytes),
                    width=request.width,
                    height=request.height,
                    purpose=request.purpose,
                    approval_status=ApprovalStatus.PROPOSED,
                    generation_request=request,
                    upload_status=UploadStatus.UPLOADED,
                    uploaded_at=timezone.now(),
                )

                generate_image_variants.enqueue(str(project_image.id))
            except Exception:
                logger.exception(
                    "Failed to save generated image from %s", gen_image.url
                )


def _get_extension(content_type: str) -> str:
    mapping = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }
    return mapping.get(content_type, "png")


def _get_preset_style(purpose: str) -> str | None:
    styles = {
        ImagePurpose.ICON: "ILLUSTRATION",
        ImagePurpose.MAIN_IMAGE: "PHOTOGRAPHY",
    }
    return styles.get(purpose)


def _delete_image_files(image: ProjectImage) -> None:
    """Delete an image and its variants from S3."""
    for variant in image.variants.all():
        try:
            storage_service.delete_object(variant.storage_key)
        except Exception:
            logger.exception("Failed to delete variant %s from S3", variant.storage_key)
    try:
        storage_service.delete_object(image.storage_key)
    except Exception:
        logger.exception("Failed to delete image %s from S3", image.storage_key)
