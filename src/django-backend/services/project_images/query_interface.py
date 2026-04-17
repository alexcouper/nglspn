from abc import ABC, abstractmethod
from uuid import UUID

from apps.projects.models import Project, ProjectImage


class ProjectImageQueryInterface(ABC):
    @abstractmethod
    def get_project_for_owner(self, project_id: UUID, owner_id: UUID) -> Project: ...

    @abstractmethod
    def get_image_for_project(
        self,
        image_id: UUID,
        project_id: UUID,
        *,
        upload_status: str | None = None,
    ) -> ProjectImage: ...

    @abstractmethod
    def count_uploaded_non_icon_images(self, project: Project) -> int: ...

    @abstractmethod
    def has_main_image(self, project: Project) -> bool: ...
