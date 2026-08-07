from __future__ import annotations

import io
import logging
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from django.db.models import QuerySet
from django.utils import timezone
from PIL import Image

from apps.projects.models import (
    VARIANT_SIZE_WIDTHS,
    ImageVariant,
    ProjectImage,
    UploadStatus,
    VariantSize,
)
from services.images.exceptions import (
    FileTooLargeError,
    ImageCapReachedError,
    UnsupportedContentTypeError,
    UploadNotCompletedError,
)
from services.images.handler_interface import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE,
    MAX_IMAGES_PER_ARTICLE,
    MAX_IMAGES_PER_PROJECT,
    FileMeta,
    ImageHandlerInterface,
    PreparedUpload,
)
from services.storage import storage_service

if TYPE_CHECKING:
    from apps.articles.models import Article
    from apps.projects.models import Project

logger = logging.getLogger(__name__)

WEBP_QUALITY = 80


class DjangoImageHandler(ImageHandlerInterface):
    # ------------------------------------------------------------------
    # Upload lifecycle
    # ------------------------------------------------------------------

    def create_gallery_upload(
        self, project: Project, meta: FileMeta, *, is_icon: bool = False
    ) -> PreparedUpload:
        self._validate(meta)
        gallery_count = self._gallery_count(project)
        # Icons sit beside the gallery rather than in it, so they neither count
        # against the cap nor take a slot's display order.
        if not is_icon and gallery_count >= MAX_IMAGES_PER_PROJECT:
            raise ImageCapReachedError(MAX_IMAGES_PER_PROJECT, "project")
        return self._reserve(
            project,
            meta,
            article=None,
            is_icon=is_icon,
            display_order=gallery_count,
        )

    def create_article_upload(self, article: Article, meta: FileMeta) -> PreparedUpload:
        self._validate(meta)
        article_count = article.images.uploaded().count()
        if article_count >= MAX_IMAGES_PER_ARTICLE:
            raise ImageCapReachedError(MAX_IMAGES_PER_ARTICLE, "article")
        return self._reserve(
            article.project,
            meta,
            article=article,
            is_icon=False,
            display_order=article_count,
        )

    def complete_upload(
        self, image: ProjectImage, *, width: int | None, height: int | None
    ) -> ProjectImage:
        if not storage_service.object_exists(image.storage_key):
            raise UploadNotCompletedError

        image.upload_status = UploadStatus.UPLOADED
        image.uploaded_at = timezone.now()
        image.width = width
        image.height = height

        # The first gallery image becomes the cover. Icons and article uploads
        # are never eligible — the project's cover must describe the project.
        if self._is_gallery_image(image) and not self._has_cover(image.project):
            image.is_main = True

        image.save()

        from api.tasks.images import generate_image_variants  # noqa: PLC0415

        generate_image_variants.enqueue(str(image.id))
        return image

    def delete_image(self, image: ProjectImage) -> None:
        # Variant rows cascade with the image; their objects do not.
        for variant in image.variants.all():
            try:
                storage_service.delete_object(variant.storage_key)
            except Exception:
                logger.exception(
                    "Failed to delete variant %s from S3", variant.storage_key
                )

        storage_service.delete_object(image.storage_key)

        was_cover = image.is_main
        project = image.project
        image.delete()

        if was_cover:
            replacement = self._gallery_queryset(project).first()
            if replacement:
                replacement.is_main = True
                replacement.save()

    # ------------------------------------------------------------------
    # Shared mechanics
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(meta: FileMeta) -> None:
        if meta.content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedContentTypeError(ALLOWED_CONTENT_TYPES)
        if meta.file_size > MAX_FILE_SIZE:
            raise FileTooLargeError(MAX_FILE_SIZE)

    @staticmethod
    def _reserve(
        project: Project,
        meta: FileMeta,
        *,
        article: Article | None,
        is_icon: bool,
        display_order: int,
    ) -> PreparedUpload:
        storage_key = storage_service.generate_upload_key(
            str(project.id),
            meta.filename,
        )
        image = ProjectImage.objects.create(
            project=project,
            article=article,
            storage_key=storage_key,
            original_filename=meta.filename,
            content_type=meta.content_type,
            file_size=meta.file_size,
            upload_status=UploadStatus.PENDING,
            display_order=display_order,
            is_icon=is_icon,
        )
        presigned = storage_service.generate_presigned_upload_url(
            storage_key,
            meta.content_type,
        )
        return PreparedUpload(
            image=image,
            upload_url=presigned["upload_url"],
            method=presigned["method"],
            headers=presigned["headers"],
            storage_key=storage_key,
        )

    @staticmethod
    def _is_gallery_image(image: ProjectImage) -> bool:
        """The single definition of "counts as one of the project's own images".

        Read off the row rather than passed in, so completion and deletion
        cannot disagree with what the upload was created as.
        """
        return not image.is_icon and image.article_id is None

    @staticmethod
    def _gallery_queryset(project: Project) -> QuerySet[ProjectImage]:
        # Deliberately not `query.gallery_images()`, despite the resemblance.
        # This one answers "what counts against the cap / may become the
        # cover", so it excludes icons. `gallery_images()` answers "what
        # describes the project" and must include them, because
        # `resolve_image_by_purpose` looks for `is_icon` in what it is handed.
        return (
            project.images.uploaded().exclude(is_icon=True).filter(article__isnull=True)
        )

    def _gallery_count(self, project: Project) -> int:
        return self._gallery_queryset(project).count()

    @staticmethod
    def _has_cover(project: Project) -> bool:
        return project.images.filter(is_main=True).exists()

    # ------------------------------------------------------------------
    # Variants
    # ------------------------------------------------------------------

    def generate_variants(self, image_id: str) -> None:
        try:
            image = ProjectImage.objects.uploaded().get(id=image_id)
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
