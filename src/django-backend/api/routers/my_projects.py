from typing import Any

from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.project import (
    CompetitionEntryRequest,
    ImageUploadCompleteRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
    ProjectCreate,
    ProjectImageResponse,
    ProjectResponse,
    PublishMissingFieldsResponse,
    UpdateImageRolesRequest,
)
from apps.projects.models import (
    Project,
    ProjectImage,
    UploadStatus,
)
from apps.users.models import User
from services import HANDLERS, REPO
from services.images.exceptions import ImageError
from services.images.handler_interface import FileMeta
from services.project.exceptions import (
    CompetitionEntryConflictError,
    InvalidCompetitionError,
    InvalidProjectStateError,
    InvalidTagsError,
    ProjectNotFoundError,
    PublishPreconditionsError,
)
from services.project.handler_interface import CreateProjectInput, UpdateProjectInput


def _with_standing(project: Project) -> Project:
    """Competition standing is a /my-projects concern; the public routes leave
    the field null."""
    return REPO.project.with_competition_standing([project])[0]


def _get_editable_project_or_404(project_id: str, user: User) -> Project:
    project = get_object_or_404(Project, id=project_id)
    if not REPO.project.user_can_edit(project.id, user.id):
        raise Http404
    return project


router = Router()


@router.get(
    "",
    response={200: list[ProjectResponse], 401: Error},
    auth=auth,
    tags=["My Projects"],
)
def list_my_projects(request: HttpRequest) -> list[Project]:
    return REPO.project.with_competition_standing(
        REPO.project.list_for_owner(request.auth.id)
    )


@router.get(
    "/tip-offs",
    response={200: list[ProjectResponse], 401: Error},
    auth=auth,
    tags=["My Projects"],
)
def list_my_tip_offs(request: HttpRequest) -> list[Project]:
    return REPO.project.with_competition_standing(
        REPO.project.list_tip_offs_for(request.auth.id)
    )


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
        is_community_tipoff=payload.is_community_tipoff,
    )
    try:
        project = HANDLERS.project.create(data)
    except InvalidTagsError as exc:
        return 400, {"detail": str(exc)}
    return 201, _with_standing(project)


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
        return _with_standing(REPO.project.get_for_owner(project_id, request.auth.id))
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
        return _with_standing(
            HANDLERS.project.update(project_id, request.auth.id, data)
        )
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
        return _with_standing(HANDLERS.project.resubmit(project_id, request.auth.id))
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
        return _with_standing(HANDLERS.project.publish(project_id, request.auth.id))
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}
    except PublishPreconditionsError as exc:
        return 400, {"detail": str(exc), "missing": exc.missing}
    except InvalidProjectStateError as exc:
        return 400, {"detail": str(exc), "missing": []}


@router.post(
    "/{project_id}/competition-entry",
    response={
        200: ProjectResponse,
        400: Error,
        401: Error,
        404: Error,
        409: Error,
    },
    auth=auth,
    tags=["My Projects"],
)
def enter_competition(
    request: HttpRequest,
    project_id: str,
    payload: CompetitionEntryRequest,
) -> Project | tuple[int, dict[str, str]]:
    try:
        project = HANDLERS.project.enter_competition(
            project_id, payload.competition_id, request.auth.id
        )
    except ProjectNotFoundError:
        return 404, {"detail": "Not Found"}
    except InvalidProjectStateError as exc:
        return 400, {"detail": str(exc)}
    except InvalidCompetitionError as exc:
        return 400, {"detail": str(exc)}
    except CompetitionEntryConflictError as exc:
        return 409, {"detail": str(exc)}
    return _with_standing(project)


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

    try:
        prepared = HANDLERS.images.create_gallery_upload(
            project,
            FileMeta(
                filename=payload.filename,
                content_type=payload.content_type,
                file_size=payload.file_size,
            ),
            is_icon=payload.is_icon,
        )
    except ImageError as exc:
        return 400, {"detail": str(exc)}

    return PresignedUploadResponse(
        image_id=prepared.image.id,
        upload_url=prepared.upload_url,
        method=prepared.method,
        headers=prepared.headers,
        storage_key=prepared.storage_key,
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
    # `get_gallery_image` keeps this endpoint off article uploads: those are
    # addressed under the articles router and completed there.
    image = REPO.images.get_gallery_image(
        project, image_id, status=UploadStatus.PENDING
    )
    if image is None:
        return 404, {"detail": "Image not found"}

    try:
        return HANDLERS.images.complete_upload(
            image, width=payload.width, height=payload.height
        )
    except ImageError as exc:
        return 400, {"detail": str(exc)}


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
    image = REPO.images.get_gallery_image(
        project, image_id, status=UploadStatus.UPLOADED
    )
    if image is None:
        return 404, {"detail": "Image not found"}

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
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    project = _get_editable_project_or_404(project_id, request.auth)
    image = REPO.images.get_gallery_image(project, image_id)
    if image is None:
        return 404, {"detail": "Image not found"}
    HANDLERS.images.delete_image(image)
    return 204, None
