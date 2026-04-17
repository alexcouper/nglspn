from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.project import (
    ImageUploadCompleteRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
    ProjectCreate,
    ProjectImageResponse,
    ProjectResponse,
    UpdateImageRolesRequest,
)
from api.tasks.images import generate_image_variants
from apps.projects.models import Project
from services import HANDLERS, REPO
from services.project.exceptions import (
    InvalidCompetitionError,
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
)
from services.project.handler_interface import CreateProjectInput, UpdateProjectInput
from services.project_images.exceptions import (
    ImageLimitExceededError,
    ProjectImageNotFoundError,
)
from services.storage import storage_service

MAX_IMAGES_PER_PROJECT = 10
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

router = Router()


@router.get(
    "",
    response={200: list[ProjectResponse], 401: Error},
    auth=auth,
    tags=["My Projects"],
)
def list_my_projects(request: HttpRequest) -> QuerySet[Project]:
    return REPO.project.list_for_owner(request.auth.id)


@router.post(
    "",
    response={201: ProjectResponse, 400: Error, 401: Error},
    auth=auth,
    tags=["My Projects"],
)
def create_project(
    request: HttpRequest,
    payload: ProjectCreate,
) -> tuple[int, Project | dict[str, Any]]:
    data = CreateProjectInput(
        owner_id=request.auth.id,
        website_url=payload.website_url,
        title=payload.title,
        tagline=payload.tagline,
        description=payload.description,
        long_description=payload.long_description,
        github_url=payload.github_url,
        demo_url=payload.demo_url,
        tech_stack=payload.tech_stack,
        tag_ids=payload.tag_ids,
        competition_id=payload.competition_id,
    )
    try:
        project = HANDLERS.project.create(data)
    except (InvalidTagsError, InvalidCompetitionError) as exc:
        return 400, {"detail": str(exc)}
    return 201, project


@router.get(
    "/{project_id}",
    response={200: ProjectResponse, 401: Error, 404: Error},
    auth=auth,
    tags=["My Projects"],
)
def get_my_project(
    request: HttpRequest, project_id: str
) -> Project | tuple[int, dict[str, str]]:
    try:
        return REPO.project.get_for_owner(project_id, request.auth.id)
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}


@router.put(
    "/{project_id}",
    response={200: ProjectResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["My Projects"],
)
def update_project(
    request: HttpRequest,
    project_id: str,
    payload: ProjectCreate,
) -> Project | tuple[int, dict[str, str]]:
    data = UpdateProjectInput(
        website_url=payload.website_url,
        title=payload.title,
        tagline=payload.tagline,
        description=payload.description,
        long_description=payload.long_description,
        github_url=payload.github_url,
        demo_url=payload.demo_url,
        tech_stack=payload.tech_stack,
        tag_ids=payload.tag_ids or [],
    )
    try:
        return HANDLERS.project.update(project_id, request.auth.id, data)
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}
    except InvalidTagsError as exc:
        return 400, {"detail": str(exc)}


@router.delete(
    "/{project_id}",
    response={204: None, 401: Error, 404: Error},
    auth=auth,
    tags=["My Projects"],
)
def delete_project(
    request: HttpRequest,
    project_id: str,
) -> tuple[int, None]:
    try:
        HANDLERS.project.delete(project_id, request.auth.id)
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}
    return 204, None


@router.post(
    "/{project_id}/resubmit",
    response={200: ProjectResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["My Projects"],
)
def resubmit_project(
    request: HttpRequest,
    project_id: str,
) -> Project | tuple[int, dict[str, str]]:
    try:
        return HANDLERS.project.resubmit(project_id, request.auth.id)
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}
    except InvalidProjectStateError as exc:
        return 400, {"detail": str(exc)}


@router.post(
    "/{project_id}/images/upload-url",
    response={200: PresignedUploadResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Project Images"],
)
def get_upload_url(
    request: HttpRequest,
    project_id: str,
    payload: PresignedUploadRequest,
) -> PresignedUploadResponse | tuple[int, dict[str, str]]:
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        return 400, {"detail": f"Content type must be one of: {allowed}"}

    if payload.file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        return 400, {"detail": f"File size must be less than {max_mb}MB"}

    try:
        project = REPO.project_images.get_project_for_owner(project_id, request.auth.id)
    except ProjectImageNotFoundError:
        return 404, {"detail": "Not Found"}

    current_count = REPO.project_images.count_uploaded_non_icon_images(project)
    if not payload.is_icon and current_count >= MAX_IMAGES_PER_PROJECT:
        return 400, {"detail": f"Maximum {MAX_IMAGES_PER_PROJECT} images per project"}

    storage_key = storage_service.generate_upload_key(
        str(project.id),
        payload.filename,
    )

    try:
        image = HANDLERS.project_images.create_image(
            project_id=project.id,
            owner_id=request.auth.id,
            storage_key=storage_key,
            original_filename=payload.filename,
            content_type=payload.content_type,
            file_size=payload.file_size,
            is_icon=payload.is_icon,
            display_order=current_count,
        )
    except ImageLimitExceededError:
        return 400, {"detail": f"Maximum {MAX_IMAGES_PER_PROJECT} images per project"}

    presigned = storage_service.generate_presigned_upload_url(
        storage_key,
        payload.content_type,
    )

    return PresignedUploadResponse(
        image_id=image.id,
        upload_url=presigned["upload_url"],
        method=presigned["method"],
        headers=presigned["headers"],
        storage_key=storage_key,
    )


@router.post(
    "/{project_id}/images/{image_id}/complete",
    response={200: ProjectImageResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Project Images"],
)
def complete_upload(
    request: HttpRequest,
    project_id: str,
    image_id: str,
    payload: ImageUploadCompleteRequest,
) -> tuple[int, Any]:
    try:
        image = REPO.project_images.get_image_for_project(
            image_id, project_id, upload_status="pending"
        )
    except ProjectImageNotFoundError:
        return 404, {"detail": "Not Found"}

    if not storage_service.object_exists(image.storage_key):
        return 400, {"detail": "Image not found in storage. Upload may have failed."}

    try:
        image = HANDLERS.project_images.complete_upload(
            project_id=project_id,
            owner_id=request.auth.id,
            image_id=image_id,
            width=payload.width,
            height=payload.height,
        )
    except ProjectImageNotFoundError:
        return 404, {"detail": "Not Found"}

    generate_image_variants.enqueue(str(image.id))

    return 200, image


@router.post(
    "/{project_id}/images/{image_id}/roles",
    response={200: ProjectImageResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Project Images"],
)
def update_image_roles(
    request: HttpRequest,
    project_id: str,
    image_id: str,
    payload: UpdateImageRolesRequest,
) -> tuple[int, Any]:
    try:
        image = HANDLERS.project_images.update_roles(
            project_id=project_id,
            owner_id=request.auth.id,
            image_id=image_id,
            is_main=payload.is_main,
            is_hero=payload.is_hero,
            is_usage=payload.is_usage,
        )
    except ProjectImageNotFoundError:
        return 404, {"detail": "Not Found"}

    return 200, image


@router.delete(
    "/{project_id}/images/{image_id}",
    response={204: None, 401: Error, 404: Error},
    auth=auth,
    tags=["Project Images"],
)
def delete_image(
    request: HttpRequest,
    project_id: str,
    image_id: str,
) -> tuple[int, None]:
    try:
        HANDLERS.project_images.delete_image(
            project_id=project_id,
            owner_id=request.auth.id,
            image_id=image_id,
        )
    except ProjectImageNotFoundError:
        return 404, {"detail": "Not Found"}

    return 204, None
