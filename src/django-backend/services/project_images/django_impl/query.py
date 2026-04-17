from uuid import UUID

from apps.projects.models import Project, ProjectImage, UploadStatus
from services.project_images.exceptions import ProjectImageNotFoundError


class DjangoProjectImageQuery:
    def get_project_for_owner(self, project_id: UUID, owner_id: UUID) -> Project:
        try:
            return Project.objects.get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectImageNotFoundError from None

    def get_image_for_project(
        self,
        image_id: UUID,
        project_id: UUID,
        *,
        upload_status: str | None = None,
    ) -> ProjectImage:
        try:
            qs = ProjectImage.objects.filter(id=image_id, project_id=project_id)
            if upload_status:
                qs = qs.filter(upload_status=upload_status)
            return qs.get()
        except ProjectImage.DoesNotExist:
            raise ProjectImageNotFoundError from None

    def count_uploaded_non_icon_images(self, project: Project) -> int:
        return (
            project.images.filter(upload_status=UploadStatus.UPLOADED)
            .exclude(is_icon=True)
            .count()
        )

    def has_main_image(self, project: Project) -> bool:
        return project.images.filter(is_main=True).exists()
