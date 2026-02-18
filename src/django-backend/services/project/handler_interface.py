from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from apps.projects.models import Project


@dataclass
class CreateProjectInput:
    owner_id: UUID
    website_url: str
    title: str | None = None
    tagline: str | None = None
    description: str | None = None
    long_description: str | None = None
    github_url: str | None = None
    demo_url: str | None = None
    tech_stack: list[str] | None = None
    tag_ids: list[UUID] | None = None
    competition_id: UUID | None = None


@dataclass
class UpdateProjectInput:
    website_url: str
    title: str | None = None
    tagline: str | None = None
    description: str | None = None
    long_description: str | None = None
    github_url: str | None = None
    demo_url: str | None = None
    tech_stack: list[str] | None = None
    tag_ids: list[UUID] = field(default_factory=list)


class ProjectHandlerInterface(ABC):
    @abstractmethod
    def create(self, data: CreateProjectInput) -> Project: ...

    @abstractmethod
    def update(
        self, project_id: UUID, owner_id: UUID, data: UpdateProjectInput
    ) -> Project: ...

    @abstractmethod
    def delete(self, project_id: UUID, owner_id: UUID) -> None: ...

    @abstractmethod
    def resubmit(self, project_id: UUID, owner_id: UUID) -> Project: ...
