from __future__ import annotations

import io
import logging
from pathlib import PurePosixPath

from PIL import Image

from apps.projects.models import (
    VARIANT_SIZE_WIDTHS,
    ImageVariant,
    ProjectImage,
    UploadStatus,
    VariantSize,
)
from services.image.handler_interface import ImageHandlerInterface
from services.storage import storage_service

logger = logging.getLogger(__name__)

WEBP_QUALITY = 80


class DjangoImageHandler(ImageHandlerInterface):
    def generate_variants(self, image_id: str) -> None:
        try:
            image = ProjectImage.objects.get(
                id=image_id, upload_status=UploadStatus.UPLOADED
            )
        except ProjectImage.DoesNotExist:
            logger.warning(
                "Image %s not found or not uploaded, skipping",
                image_id,
            )
            return

        try:
            original_bytes = storage_service.download_object(image.storage_key)
        except Exception:
            logger.exception("Failed to download original image %s from S3", image_id)
            return

        try:
            img = Image.open(io.BytesIO(original_bytes))
            img.load()
        except Exception:
            logger.exception("Failed to decode image %s", image_id)
            return

        original_width = image.width
        if not original_width:
            # Fallback: read dimensions from the decoded image and backfill the DB
            original_width = img.width
            image.width = img.width
            image.height = img.height
            image.save(update_fields=["width", "height"])
            logger.info(
                "Backfilled dimensions for image %s from Pillow (%dx%d)",
                image_id,
                img.width,
                img.height,
            )

        # Strip the file extension from the storage key to build variant paths
        p = PurePosixPath(image.storage_key)
        base_key = str(p.parent / p.stem)

        for size in VariantSize:
            target_width = VARIANT_SIZE_WIDTHS[size]

            if target_width >= original_width:
                continue

            # Skip if this variant already exists
            if ImageVariant.objects.filter(image=image, size=size).exists():
                continue

            try:
                self._generate_single_variant(img, image, base_key, size, target_width)
            except Exception:
                logger.exception(
                    "Failed to generate %s variant for image %s", size, image_id
                )

    def _generate_single_variant(
        self,
        img: Image.Image,
        image: ProjectImage,
        base_key: str,
        size: str,
        target_width: int,
    ) -> None:
        # Calculate proportional height
        ratio = target_width / img.width
        target_height = round(img.height * ratio)

        # Resize with high-quality resampling
        resized = img.copy()
        resized.thumbnail((target_width, target_height), Image.LANCZOS)

        # Encode to WebP
        buffer = io.BytesIO()
        resized.save(buffer, format="WEBP", quality=WEBP_QUALITY)
        webp_bytes = buffer.getvalue()

        # Upload to S3
        variant_key = f"{base_key}/{size}.webp"
        storage_service.upload_object(variant_key, webp_bytes, "image/webp")

        # Record in DB
        ImageVariant.objects.create(
            image=image,
            size=size,
            storage_key=variant_key,
            width=resized.width,
            height=resized.height,
            file_size=len(webp_bytes),
        )
