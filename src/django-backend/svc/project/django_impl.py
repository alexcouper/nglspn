from math import ceil
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.projects.models import (
    Competition,
    CompetitionStatus,
    Project,
    ProjectStatus,
)
from apps.tags.models import Tag, TagStatus
from svc.project.exceptions import (
    InvalidCompetitionError,
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
)
from svc.project.handler_interface import (
    CreateProjectInput,
    ProjectHandlerInterface,
    UpdateProjectInput,
)
from svc.project.query_interface import ProjectQueryInterface


def _base_queryset() -> QuerySet[Project]:
    return Project.objects.select_related("owner").prefetch_related(
        "tags", "tags__category", "won_competitions"
    )


def get_title_from_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    parsed_url = urlparse(url)
    domain = parsed_url.netloc or parsed_url.path

    domain = domain.replace("www.", "")
    if domain == "github.com":
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 2:  # noqa: PLR2004
            return path_parts[1]

    return domain or "Untitled Project"


class DjangoProjectQuery(ProjectQueryInterface):
    def get_by_id(self, project_id: UUID) -> Project:
        try:
            return _base_queryset().get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

    def get_for_owner(self, project_id: UUID, owner_id: UUID) -> Project:
        try:
            return _base_queryset().get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None

    def list_approved(
        self,
        *,
        tags: list[str] | None = None,
        tech_stack: list[str] | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        queryset = _base_queryset().filter(status=ProjectStatus.APPROVED)

        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        if tech_stack:
            for tech in tech_stack:
                queryset = queryset.filter(tech_stack__icontains=tech)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search),
            )

        order_field = f"-{sort_by}" if sort_order == "desc" else sort_by
        queryset = queryset.order_by(order_field)

        total = queryset.count()
        pages = ceil(total / per_page)
        offset = (page - 1) * per_page
        projects = queryset[offset : offset + per_page]

        return {
            "projects": projects,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    def list_for_owner(self, owner_id: UUID) -> QuerySet[Project]:
        return _base_queryset().filter(owner_id=owner_id)

    def list_featured(self, limit: int = 10) -> QuerySet[Project]:
        return _base_queryset().filter(status=ProjectStatus.APPROVED, is_featured=True)[
            :limit
        ]

    def list_trending(self, limit: int = 10) -> QuerySet[Project]:
        return (
            _base_queryset()
            .filter(status=ProjectStatus.APPROVED)
            .order_by("-monthly_visitors")[:limit]
        )

    def count_pending(self) -> int:
        return Project.objects.filter(status=ProjectStatus.PENDING).count()

    def get_project_with_owner(self, project_id: UUID) -> dict[str, Any]:
        try:
            project = Project.objects.select_related("owner").get(id=project_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None
        return {
            "id": project.id,
            "title": project.title,
            "owner_email": project.owner.email,
            "owner_first_name": project.owner.first_name,
        }


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

        return project

    def delete(self, project_id: UUID, owner_id: UUID) -> None:
        try:
            project = Project.objects.get(id=project_id, owner_id=owner_id)
        except Project.DoesNotExist:
            raise ProjectNotFoundError from None
        project.delete()

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
