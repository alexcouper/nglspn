from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from api.tasks.web_ui import revalidate_project
from apps.projects.models import (
    Competition,
    CompetitionStatus,
    Project,
    ProjectStatus,
)
from apps.tags.models import Tag, TagStatus
from services.project.exceptions import (
    InvalidCompetitionError,
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
)
from services.project.handler_interface import ProjectHandlerInterface

from .query import get_title_from_url

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from services.project.handler_interface import (
        CreateProjectInput,
        UpdateProjectInput,
    )


def _validate_tags(tag_ids: list[UUID]) -> QuerySet[Tag]:
    valid_tags = Tag.objects.filter(id__in=tag_ids).exclude(status=TagStatus.REJECTED)
    if len(tag_ids) != valid_tags.count():
        msg = "One or more tag IDs are invalid or rejected"
        raise InvalidTagsError(msg)
    return valid_tags


class DjangoProjectHandler(ProjectHandlerInterface):
    def create(self, data: CreateProjectInput) -> Project:
        valid_tags = None
        if data.tag_ids:
            valid_tags = _validate_tags(data.tag_ids)

        competition = None
        if data.competition_id:
            try:
                competition = Competition.objects.get(id=data.competition_id)
            except Competition.DoesNotExist:
                msg = "Competition not found"
                raise InvalidCompetitionError(msg) from None
            if competition.status != CompetitionStatus.ACCEPTING_APPLICATIONS:
                msg = "Competition is not accepting applications"
                raise InvalidCompetitionError(msg)
        else:
            competition = (
                Competition.objects.filter(
                    status=CompetitionStatus.ACCEPTING_APPLICATIONS
                )
                .order_by("-start_date")
                .first()
            )

        project_fields: dict[str, Any] = {
            "owner_id": data.owner_id,
            "website_url": data.website_url,
        }
        for field in (
            "title",
            "tagline",
            "description",
            "long_description",
            "github_url",
            "demo_url",
            "tech_stack",
        ):
            value = getattr(data, field)
            if value is not None:
                project_fields[field] = value

        if not project_fields.get("title"):
            project_fields["title"] = get_title_from_url(data.website_url)

        project = Project.objects.create(**project_fields)

        if valid_tags is not None:
            project.tags.set(valid_tags)

        if competition:
            competition.projects.add(project)

        revalidate_project.enqueue(str(project.id))

        return project

    def update(
        self, project_id: UUID, owner_id: UUID, data: UpdateProjectInput
    ) -> Project:
        try:
            project = Project.objects.get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

        valid_tags = _validate_tags(data.tag_ids) if data.tag_ids else None

        update_fields: dict[str, Any] = {"website_url": data.website_url}
        for field in (
            "title",
            "tagline",
            "description",
            "long_description",
            "github_url",
            "demo_url",
            "tech_stack",
        ):
            value = getattr(data, field)
            if value is not None:
                update_fields[field] = value

        if not update_fields.get("title"):
            parsed_url = urlparse(data.website_url)
            domain = parsed_url.netloc or parsed_url.path
            domain = domain.replace("www.", "")
            update_fields["title"] = domain or "Untitled Project"

        for field, value in update_fields.items():
            setattr(project, field, value)

        if project.status == ProjectStatus.REJECTED:
            project.status = ProjectStatus.PENDING
            project.rejection_reason = None

        project.save()

        if valid_tags is not None:
            project.tags.set(valid_tags)
        else:
            project.tags.clear()

        revalidate_project.enqueue(str(project.id))
        return project

    def delete(self, project_id: UUID, owner_id: UUID) -> None:
        try:
            project = Project.objects.get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None
        pid = str(project.id)
        project.delete()
        revalidate_project.enqueue(pid)

    def resubmit(self, project_id: UUID, owner_id: UUID) -> Project:
        try:
            project = Project.objects.get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

        if project.status != ProjectStatus.REJECTED:
            msg = "Only rejected projects can be resubmitted"
            raise InvalidProjectStateError(msg)

        project.status = ProjectStatus.PENDING
        project.rejection_reason = None
        project.save()

        return project
