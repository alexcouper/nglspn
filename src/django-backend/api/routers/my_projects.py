import logging
from typing import Any

from django.db.models import QuerySet
from django.http import Http404, HttpRequest
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
    PublishMissingFieldsResponse,
    UpdateImageRolesRequest,
)
from api.tasks.images import generate_image_variants
from apps.projects.models import (
    Project,
    ProjectImage,
    UploadStatus,
)
from apps.users.models import User
from services import HANDLERS, REPO
from services.project.exceptions import (
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
    PublishPreconditionsError,
)
from services.project.handler_interface import CreateProjectInput, UpdateProjectInput
from services.storage import storage_service


def _get_editable_project_or_404(project_id: str, user: User) -> Project:
    project = get_object_or_404(Project, id=project_id)
    if not REPO.project.user_can_edit(project.id, user.id):
        raise Http404
    return project


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


@router.get(
    "/suggestions",
    response={200: list[ProjectResponse], 401: Error},
    auth=auth,
    tags=["My Projects"],
)
def list_my_suggestions(request: HttpRequest) -> QuerySet[Project]:
    return REPO.project.list_suggestions_for(request.auth.id)


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
        community_owned=payload.community_owned,
    )
    try:
        project = HANDLERS.project.create(data)
    except InvalidTagsError as exc:
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
    "/{project_id}/publish",
    response={
        200: ProjectResponse,
        400: PublishMissingFieldsResponse,
        401: Error,
        404: Error,
    },
    auth=auth,
    tags=["My Projects"],
)
def publish_project(
    request: HttpRequest,
    project_id: str,
) -> Project | tuple[int, dict[str, Any]]:
    try:
        return HANDLERS.project.publish(project_id, request.auth.id)
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}
    except PublishPreconditionsError as exc:
        return 400, {"detail": str(exc), "missing": exc.missing}
    except InvalidProjectStateError as exc:
        return 400, {"detail": str(exc), "missing": []}


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
    project = _get_editable_project_or_404(project_id, request.auth)

    # Validate content type
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        return 400, {"detail": f"Content type must be one of: {allowed}"}

    # Validate file size
    if payload.file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        return 400, {"detail": f"File size must be less than {max_mb}MB"}

    is_icon = payload.is_icon

    # Check image count limit (icons don't count)
    current_count = (
        project.images.filter(upload_status=UploadStatus.UPLOADED)
        .exclude(is_icon=True)
        .count()
    )
    if not is_icon and current_count >= MAX_IMAGES_PER_PROJECT:
        return 400, {"detail": f"Maximum {MAX_IMAGES_PER_PROJECT} images per project"}

    # Generate storage key
    storage_key = storage_service.generate_upload_key(
        str(project.id),
        payload.filename,
    )

    image = ProjectImage.objects.create(
        project=project,
        storage_key=storage_key,
        original_filename=payload.filename,
        content_type=payload.content_type,
        file_size=payload.file_size,
        upload_status=UploadStatus.PENDING,
        display_order=current_count,
        is_icon=is_icon,
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
    project = _get_editable_project_or_404(project_id, request.auth)
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

    # If this is the first non-icon image, make it the main image
    is_icon = image.is_icon
    has_main = project.images.filter(is_main=True).exists()
    if not is_icon and not has_main:
        image.is_main = True

    image.save()

    # Enqueue async variant generation
    generate_image_variants.enqueue(str(image.id))

    return image


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
) -> ProjectImage | tuple[int, dict[str, str]]:
    project = _get_editable_project_or_404(project_id, request.auth)
    image = get_object_or_404(
        ProjectImage,
        id=image_id,
        project=project,
        upload_status=UploadStatus.UPLOADED,
    )

    role_fields = [
        ("is_main", payload.is_main),
        ("is_hero", payload.is_hero),
        ("is_usage", payload.is_usage),
    ]

    for field, value in role_fields:
        if value is None:
            continue
        if value:
            # Clear this role from all other images on the project
            project.images.exclude(id=image.id).filter(**{field: True}).update(
                **{field: False}
            )
        setattr(image, field, value)

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
    project = _get_editable_project_or_404(project_id, request.auth)
    image = get_object_or_404(ProjectImage, id=image_id, project=project)

    # Delete variant files from S3 (DB rows cascade-delete with the image)
    for variant in image.variants.all():
        try:
            storage_service.delete_object(variant.storage_key)
        except Exception:
            logging.getLogger(__name__).exception(
                "Failed to delete variant %s from S3", variant.storage_key
            )

    # Delete original from storage
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
