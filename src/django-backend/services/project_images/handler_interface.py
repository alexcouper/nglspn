from abc import ABC, abstractmethod
from uuid import UUID

from apps.projects.models import ProjectImage


class ProjectImageHandlerInterface(ABC):
    @abstractmethod
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
    ) -> ProjectImage: ...

    @abstractmethod
    def complete_upload(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        image_id: UUID,
        width: int,
        height: int,
    ) -> ProjectImage: ...

    @abstractmethod
    def update_roles(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        image_id: UUID,
        is_main: bool | None = None,
        is_hero: bool | None = None,
        is_usage: bool | None = None,
    ) -> ProjectImage: ...

    @abstractmethod
    def delete_image(
        self,
        *,
        project_id: UUID,
        owner_id: UUID,
        image_id: UUID,
    ) -> None: ...
