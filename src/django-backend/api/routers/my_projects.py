from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
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
    SetMainImageRequest,
)
from api.services.storage import storage_service
from apps.projects.models import (
    Project,
    ProjectImage,
    UploadStatus,
)
from svc import HANDLERS, REPO
from svc.project.exceptions import (
    InvalidCompetitionError,
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
)
from svc.project.handler_interface import CreateProjectInput, UpdateProjectInput

# Image upload configuration
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


# ============================================================================
# Image Upload Endpoints
# ============================================================================


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
    """Generate a presigned URL for uploading an image."""
    project = get_object_or_404(Project, id=project_id, owner=request.auth)

    # Validate content type
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        return 400, {"detail": f"Content type must be one of: {allowed}"}

    # Validate file size
    if payload.file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        return 400, {"detail": f"File size must be less than {max_mb}MB"}

    # Check image count limit
    current_count = project.images.filter(upload_status=UploadStatus.UPLOADED).count()
    if current_count >= MAX_IMAGES_PER_PROJECT:
        return 400, {"detail": f"Maximum {MAX_IMAGES_PER_PROJECT} images per project"}

    # Generate storage key
    storage_key = storage_service.generate_upload_key(
        str(project.id),
        payload.filename,
    )

    # Create pending image record
    image = ProjectImage.objects.create(
        project=project,
        storage_key=storage_key,
        original_filename=payload.filename,
        content_type=payload.content_type,
        file_size=payload.file_size,
        upload_status=UploadStatus.PENDING,
        display_order=current_count,
    )

    # Generate presigned URL
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
) -> ProjectImage | tuple[int, dict[str, str]]:
    """Mark an image upload as complete."""
    project = get_object_or_404(Project, id=project_id, owner=request.auth)
    image = get_object_or_404(
        ProjectImage,
        id=image_id,
        project=project,
        upload_status=UploadStatus.PENDING,
    )

    # Verify the object exists in storage
    if not storage_service.object_exists(image.storage_key):
        return 400, {"detail": "Image not found in storage. Upload may have failed."}

    # Update image record
    image.upload_status = UploadStatus.UPLOADED
    image.uploaded_at = timezone.now()
    image.width = payload.width
    image.height = payload.height

    # If this is the first image, make it the main image
    if not project.images.filter(is_main=True).exists():
        image.is_main = True

    image.save()
    return image


@router.post(
    "/{project_id}/images/main",
    response={200: ProjectImageResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Project Images"],
)
def set_main_image(
    request: HttpRequest,
    project_id: str,
    payload: SetMainImageRequest,
) -> ProjectImage | tuple[int, dict[str, str]]:
    """Set the main image for a project."""
    project = get_object_or_404(Project, id=project_id, owner=request.auth)
    image = get_object_or_404(
        ProjectImage,
        id=payload.image_id,
        project=project,
        upload_status=UploadStatus.UPLOADED,
    )

    # Clear existing main image
    project.images.filter(is_main=True).update(is_main=False)

    # Set new main image
    image.is_main = True
    image.save()

    return image


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
    """Delete a project image."""
    project = get_object_or_404(Project, id=project_id, owner=request.auth)
    image = get_object_or_404(ProjectImage, id=image_id, project=project)

    # Delete from storage
    storage_service.delete_object(image.storage_key)

    was_main = image.is_main
    image.delete()

    # If deleted image was main, promote the first remaining image
    if was_main:
        first_image = project.images.filter(upload_status=UploadStatus.UPLOADED).first()
        if first_image:
            first_image.is_main = True
            first_image.save()

    return 204, None
