from math import ceil
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from django.db.models import Prefetch, Q, QuerySet

from apps.projects.models import Project, ProjectImage, ProjectStatus
from services.project.exceptions import ProjectNotFoundError
from services.project.query_interface import (
    PaginatedProjects,
    ProjectListItem,
    ProjectQueryInterface,
)

ALLOWED_SORT_FIELDS = {"created_at", "title", "updated_at"}


def _base_queryset() -> QuerySet[Project]:
    return Project.objects.select_related("owner").prefetch_related(
        "tags",
        "tags__category",
        "won_competitions",
        Prefetch(
            "images",
            queryset=ProjectImage.objects.filter(
                upload_status="uploaded"
            ).prefetch_related("variants"),
        ),
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


def to_list_item(project: Project) -> ProjectListItem:
    images = list(project.images.all())
    main_image = next((img for img in images if img.is_main), None)
    if not main_image and images:
        main_image = images[0]

    thumb_url = None
    if main_image:
        thumb = next(
            (v for v in main_image.variants.all() if v.size == "thumb"),
            None,
        )
        if thumb:
            thumb_url = thumb.url

    return ProjectListItem(
        project=project,
        main_image_url=main_image.url if main_image else None,
        main_image_thumb_url=thumb_url,
        tags=[t for t in project.tags.all() if t.status != "rejected"],
    )


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
    ) -> PaginatedProjects:
        if sort_by not in ALLOWED_SORT_FIELDS:
            allowed = ", ".join(sorted(ALLOWED_SORT_FIELDS))
            msg = f"Invalid sort field: {sort_by}. Allowed: {allowed}"
            raise ValueError(msg)

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

        return PaginatedProjects(
            projects=[to_list_item(p) for p in projects],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    def list_for_owner(self, owner_id: UUID) -> QuerySet[Project]:
        return _base_queryset().filter(owner_id=owner_id)

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
