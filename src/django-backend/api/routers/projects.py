from typing import TYPE_CHECKING, Any

from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Query, Router

from api.auth.jwt import get_user_from_token
from api.schemas.errors import Error
from api.schemas.project import ProjectListResponse, ProjectResponse
from apps.projects.models import Project, ProjectStatus
from services import REPO
from services.project.exceptions import ProjectNotFoundError

if TYPE_CHECKING:
    from apps.users.models import User

router = Router()


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
    result["pending_projects_count"] = REPO.project.count_pending()
    return result


@router.get("/featured", response={200: list[ProjectResponse]}, tags=["Projects"])
def get_featured_projects(
    request: HttpRequest,
) -> QuerySet[Project]:
    return REPO.project.list_featured()


@router.get("/trending", response={200: list[ProjectResponse]}, tags=["Projects"])
def get_trending_projects(
    request: HttpRequest,
) -> QuerySet[Project]:
    return REPO.project.list_trending()


def _get_user_from_request(request: HttpRequest) -> "User | None":
    """Extract user from Authorization header if present."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return get_user_from_token(token)
    return None


@router.get(
    "/{project_id}",
    response={200: ProjectResponse, 404: Error},
    tags=["Projects"],
)
def get_project(
    request: HttpRequest,
    project_id: str,
) -> Project | tuple[int, dict[str, str]]:
    try:
        project = REPO.project.get_by_id(project_id)
    except ProjectNotFoundError:
        return 404, {"detail": "Project not found"}

    # Approved projects are visible to everyone
    if project.status == ProjectStatus.APPROVED:
        return project

    # Non-approved projects only visible to owner or admin
    user = _get_user_from_request(request)
    if user and (project.owner == user or user.is_superuser):
        return project

    return 404, {"detail": "Project not found"}
