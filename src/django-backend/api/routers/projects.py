from typing import TYPE_CHECKING, Any

from django.http import HttpRequest
from ninja import Query, Router

from api.auth.jwt import get_user_from_token
from api.schemas.errors import Error
from api.schemas.project import (
    CategoryResponse,
    DiscoverProjectResponse,
    ProjectListItemResponse,
    ProjectListResponse,
    ProjectResponse,
    WinnerProjectResponse,
)
from apps.projects.models import Project, ProjectStatus
from services import REPO
from services.project.exceptions import ProjectNotFoundError
from services.project.permissions import user_can_edit_project

if TYPE_CHECKING:
    from apps.users.models import User

router = Router()


@router.get(
    "/categories",
    response={200: list[CategoryResponse]},
    tags=["Projects"],
)
def list_categories(request: HttpRequest) -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "project_count": c.project_count,
        }
        for c in REPO.project.list_categories()
    ]


@router.get(
    "/featured",
    response={200: list[DiscoverProjectResponse]},
    tags=["Projects"],
)
def list_featured(request: HttpRequest) -> list[DiscoverProjectResponse]:
    return [
        DiscoverProjectResponse.from_discover_item(item)
        for item in REPO.project.list_featured()
    ]


@router.get(
    "/new-arrivals",
    response={200: list[DiscoverProjectResponse]},
    tags=["Projects"],
)
def list_new_arrivals(request: HttpRequest) -> list[DiscoverProjectResponse]:
    return [
        DiscoverProjectResponse.from_discover_item(item)
        for item in REPO.project.list_new_arrivals()
    ]


@router.get(
    "/winners",
    response={200: list[WinnerProjectResponse]},
    tags=["Projects"],
)
def list_winners(request: HttpRequest) -> list[WinnerProjectResponse]:
    return [
        WinnerProjectResponse(
            id=w.project.id,
            slug=w.project.slug,
            title=w.project.title,
            tagline=w.project.tagline,
            icon_url=w.icon_url,
            hero_banner_url=w.hero_banner_url,
            in_use_image_url=w.in_use_image_url,
            competition_name=w.competition_name,
            competition_slug=w.competition_slug,
            competition_submission_deadline=w.competition_submission_deadline.isoformat()
            if w.competition_submission_deadline
            else "",
        )
        for w in REPO.project.list_winners()
    ]


@router.get(
    "/most-discussed",
    response={200: list[DiscoverProjectResponse]},
    tags=["Projects"],
)
def list_most_discussed(request: HttpRequest) -> list[DiscoverProjectResponse]:
    return [
        DiscoverProjectResponse.from_discover_item(item)
        for item in REPO.project.list_most_discussed()
    ]


@router.get(
    "/by-category/{slug}",
    response={200: list[DiscoverProjectResponse], 404: Error},
    tags=["Projects"],
)
def list_by_category(
    request: HttpRequest,
    slug: str,
    sort: str = Query("newest"),
) -> list[DiscoverProjectResponse] | tuple[int, dict[str, str]]:
    try:
        items = REPO.project.list_by_category(slug, sort)
    except ProjectNotFoundError:
        return 404, {"detail": "Category not found"}
    return [DiscoverProjectResponse.from_discover_item(item) for item in items]


@router.get("", response={200: ProjectListResponse, 400: Error}, tags=["Projects"])
def list_projects(
    request: HttpRequest,
    tags: list[str] | None = Query(None),
    tech_stack: list[str] | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    search: str | None = Query(None),
    page: int = Query(1),
    per_page: int = Query(20),
) -> dict[str, Any] | tuple[int, dict[str, str]]:
    try:
        result = REPO.project.list_approved(
            tags=tags,
            tech_stack=tech_stack,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        return 400, {"detail": str(e)}
    return {
        "projects": [
            ProjectListItemResponse.from_list_item(p) for p in result.projects
        ],
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "pages": result.pages,
        "pending_projects_count": REPO.project.count_pending(),
    }


def _get_user_from_request(request: HttpRequest) -> "User | None":
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return get_user_from_token(token)
    return None


@router.get(
    "/{identifier}",
    response={200: ProjectResponse, 404: Error},
    tags=["Projects"],
)
def get_project(
    request: HttpRequest,
    identifier: str,
) -> Project | tuple[int, dict[str, str]]:
    try:
        project = REPO.project.get_by_identifier(identifier)
    except ProjectNotFoundError:
        return 404, {"detail": "Project not found"}

    if project.status == ProjectStatus.APPROVED:
        return project

    user = _get_user_from_request(request)
    if user and (user.is_superuser or user_can_edit_project(project, user)):
        return project

    return 404, {"detail": "Project not found"}
