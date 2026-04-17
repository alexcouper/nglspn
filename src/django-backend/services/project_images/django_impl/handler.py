import logging
from uuid import UUID

from django.utils import timezone

from apps.projects.models import ProjectImage, UploadStatus
from services.project_images.exceptions import (
    ImageLimitExceededError,
)
from services.project_images.query_interface import ProjectImageQueryInterface
from services.storage import storage_service

MAX_IMAGES_PER_PROJECT = 10

logger = logging.getLogger(__name__)


class DjangoProjectImageHandler:
    @property
    def _query(self) -> ProjectImageQueryInterface:
        from services import REPO  # noqa: PLC0415

        return REPO.project_images

    def create_image(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        storage_key: str,
        original_filename: str,
        content_type: str,
        file_size: int,
        is_icon: bool,
        display_order: int,
    ) -> ProjectImage:
        project = self._query.get_project_for_owner(project_id, owner_id)

        if not is_icon:
            current_count = self._query.count_uploaded_non_icon_images(project)
            if current_count >= MAX_IMAGES_PER_PROJECT:
                raise ImageLimitExceededError

        return ProjectImage.objects.create(
            project=project,
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            file_size=file_size,
            upload_status=UploadStatus.PENDING,
            display_order=display_order,
            is_icon=is_icon,
        )

    def complete_upload(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        image_id: UUID,
        width: int,
        height: int,
    ) -> ProjectImage:
        project = self._query.get_project_for_owner(project_id, owner_id)
        image = self._query.get_image_for_project(
            image_id, project_id, upload_status=UploadStatus.PENDING
        )

        image.upload_status = UploadStatus.UPLOADED
        image.uploaded_at = timezone.now()
        image.width = width
        image.height = height

        is_icon = image.is_icon
        has_main = self._query.has_main_image(project)
        if not is_icon and not has_main:
            image.is_main = True

        image.save()
        return image

    def update_roles(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        image_id: UUID,
        is_main: bool | None = None,
        is_hero: bool | None = None,
        is_usage: bool | None = None,
    ) -> ProjectImage:
        project = self._query.get_project_for_owner(project_id, owner_id)
        image = self._query.get_image_for_project(
            image_id, project_id, upload_status=UploadStatus.UPLOADED
        )

        role_fields = [
            ("is_main", is_main),
            ("is_hero", is_hero),
            ("is_usage", is_usage),
        ]

        for field, value in role_fields:
            if value is None:
                continue
            if value:
                project.images.exclude(id=image.id).filter(**{field: True}).update(
                    **{field: False}
                )
            setattr(image, field, value)

        image.save()
        return image

    def delete_image(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        image_id: UUID,
    ) -> None:
        self._query.get_project_for_owner(project_id, owner_id)
        image = self._query.get_image_for_project(image_id, project_id)

        for variant in image.variants.all():
            try:
                storage_service.delete_object(variant.storage_key)
            except Exception:
                logger.exception(
                    "Failed to delete variant %s from S3", variant.storage_key
                )

        storage_service.delete_object(image.storage_key)

        was_main = image.is_main
        image.delete()

        if was_main:
            project = self._query.get_project_for_owner(project_id, owner_id)
            first_image = project.images.filter(
                upload_status=UploadStatus.UPLOADED
            ).first()
            if first_image:
                first_image.is_main = True
                first_image.save()
