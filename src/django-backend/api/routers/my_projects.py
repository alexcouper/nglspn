from typing import Any
from urllib.parse import urlparse

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
    Competition,
    CompetitionStatus,
    Project,
    ProjectImage,
    ProjectStatus,
    UploadStatus,
)
from apps.tags.models import Tag, TagStatus

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
    return (
        Project.objects.filter(owner=request.auth)
        .select_related("owner")
        .prefetch_related("tags", "tags__category", "won_competitions")
    )


def get_title_from_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "http://" + url  # Add scheme if missing for proper parsing

    parsed_url = urlparse(url)
    domain = parsed_url.netloc or parsed_url.path

    # Clean up the domain (remove www., etc.)
    domain = domain.replace("www.", "")
    if domain == "github.com":
        # Special handling for GitHub URLs to extract repo name
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 2:  # noqa: PLR2004
            return path_parts[1]  # Return repo name

    return domain or "Untitled Project"


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
    # Validate tag IDs exist and are not rejected (if provided)
    tag_ids = payload.tag_ids
    if tag_ids:
        valid_tags = Tag.objects.filter(id__in=tag_ids).exclude(
            status=TagStatus.REJECTED
        )
        if len(tag_ids) != valid_tags.count():
            return 400, {"detail": "One or more tag IDs are invalid or rejected"}

    # Validate competition if specified
    competition = None
    if payload.competition_id:
        try:
            competition = Competition.objects.get(id=payload.competition_id)
        except Competition.DoesNotExist:
            return 400, {"detail": "Competition not found"}
        if competition.status != CompetitionStatus.ACCEPTING_APPLICATIONS:
            return 400, {"detail": "Competition is not accepting applications"}
    else:
        # Find the most recent open competition
        competition = (
            Competition.objects.filter(status=CompetitionStatus.ACCEPTING_APPLICATIONS)
            .order_by("-start_date")
            .first()
        )

    # Prepare project data
    project_data = payload.dict(
        exclude={"tag_ids", "competition_id"}, exclude_none=True
    )

    # Auto-generate title from URL if not provided
    if not project_data.get("title"):
        project_data["title"] = get_title_from_url(payload.website_url)

    # Create project
    project = Project.objects.create(owner=request.auth, **project_data)

    # Add tags (if provided)
    if tag_ids:
        project.tags.set(valid_tags)

    # Add project to competition (if found)
    if competition:
        competition.projects.add(project)

    return 201, project


@router.get(
    "/{project_id}",
    response={200: ProjectResponse, 401: Error, 404: Error},
    auth=auth,
    tags=["My Projects"],
)
def get_my_project(request: HttpRequest, project_id: str) -> Project:
    qs = Project.objects.select_related("owner").prefetch_related(
        "tags", "tags__category", "won_competitions"
    )
    return get_object_or_404(qs, id=project_id, owner=request.auth)


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
    project = get_object_or_404(Project, id=project_id, owner=request.auth)

    # Validate tag IDs exist and are not rejected (if provided)
    tag_ids = payload.tag_ids
    if tag_ids:
        valid_tags = Tag.objects.filter(id__in=tag_ids).exclude(
            status=TagStatus.REJECTED
        )
        if len(tag_ids) != valid_tags.count():
            return 400, {"detail": "One or more tag IDs are invalid or rejected"}

    # Prepare project data
    project_data = payload.dict(exclude={"tag_ids"}, exclude_none=True)

    # Auto-generate title from URL if not provided
    if not project_data.get("title"):
        parsed_url = urlparse(payload.url)
        domain = parsed_url.netloc or parsed_url.path
        domain = domain.replace("www.", "")
        project_data["title"] = domain or "Untitled Project"

    # Update project fields
    for field, value in project_data.items():
        setattr(project, field, value)

    # Reset status to pending if it was previously rejected
    if project.status == ProjectStatus.REJECTED:
        project.status = ProjectStatus.PENDING
        project.rejection_reason = None

    project.save()

    # Update tags (if provided)
    if tag_ids:
        project.tags.set(valid_tags)
    else:
        project.tags.clear()

    return project


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
    project = get_object_or_404(Project, id=project_id, owner=request.auth)
    project.delete()
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
    project = get_object_or_404(Project, id=project_id, owner=request.auth)

    if project.status != ProjectStatus.REJECTED:
        return 400, {"detail": "Only rejected projects can be resubmitted"}

    project.status = ProjectStatus.PENDING
    project.rejection_reason = None
    project.save()

    return project


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
