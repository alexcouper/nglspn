from typing import Any
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.image_generation import (
    AdminProjectListItem,
    AdminProjectListResponse,
    ImageCompleteness,
    ProjectImagesGroupedResponse,
    ProposedImageResponse,
    PurposeImageSlot,
)
from apps.projects.models import (
    ApprovalStatus,
    ImagePurpose,
    Project,
    ProjectImage,
    ProjectStatus,
)

router = Router()

MAX_VARIANTS = 4


def _is_admin(user: Any) -> bool:
    return user.groups.filter(name="ADMIN").exists() or user.is_superuser


def _image_status(
    purpose: str,
    images: list[ProjectImage],
) -> str:
    purpose_imgs = [i for i in images if i.purpose == purpose]
    if any(i.approval_status == ApprovalStatus.ACTIVE for i in purpose_imgs):
        return "active"
    if any(i.approval_status == ApprovalStatus.PROPOSED for i in purpose_imgs):
        return "proposed"
    return "missing"


def _image_to_response(
    img: ProjectImage,
) -> ProposedImageResponse:
    return ProposedImageResponse(
        id=img.id,
        url=img.url,
        width=img.width,
        height=img.height,
        variants=[
            {
                "size": v.size,
                "url": v.url,
                "width": v.width,
                "height": v.height,
            }
            for v in img.variants.all()
        ],
    )


def _slot_for(
    purpose: str,
    all_images: list[ProjectImage],
) -> PurposeImageSlot:
    purpose_images = [img for img in all_images if img.purpose == purpose]
    return PurposeImageSlot(
        active=[
            _image_to_response(i)
            for i in purpose_images
            if i.approval_status == ApprovalStatus.ACTIVE
        ],
        proposed=[
            _image_to_response(i)
            for i in purpose_images
            if i.approval_status == ApprovalStatus.PROPOSED
        ],
    )


@router.get(
    "",
    response={
        200: AdminProjectListResponse,
        401: Error,
        403: Error,
    },
    auth=auth,
    tags=["Admin"],
)
def list_admin_projects(
    request: HttpRequest,
    status_filter: str | None = None,
) -> tuple[int, AdminProjectListResponse] | tuple[int, dict]:
    if not _is_admin(request.auth):
        return 403, {"detail": "Admin access required"}

    projects = (
        Project.objects.filter(status=ProjectStatus.APPROVED)
        .select_related("owner")
        .prefetch_related(
            "images",
            "images__variants",
            "won_competitions",
        )
        .order_by("-created_at")
    )

    result = []
    for project in projects:
        all_images = list(project.images.all())
        is_winner = project.won_competitions.exists()

        completeness = ImageCompleteness(
            icon=_image_status(ImagePurpose.ICON, all_images),
            main_image=_image_status(ImagePurpose.MAIN_IMAGE, all_images),
            winner_composite=(
                _image_status(ImagePurpose.WINNER_COMPOSITE, all_images)
                if is_winner
                else None
            ),
        )

        if status_filter == "missing":
            has_missing = (
                completeness.icon == "missing"
                or completeness.main_image == "missing"
                or completeness.winner_composite == "missing"
            )
            if not has_missing:
                continue
        elif status_filter == "proposed":
            has_proposed = (
                completeness.icon == "proposed"
                or completeness.main_image == "proposed"
                or completeness.winner_composite == "proposed"
            )
            if not has_proposed:
                continue

        result.append(
            AdminProjectListItem(
                id=project.id,
                title=project.title,
                owner_email=project.owner.email,
                image_completeness=completeness,
                created_at=project.created_at,
            )
        )

    return 200, AdminProjectListResponse(
        projects=result,
        total=len(result),
    )


@router.get(
    "/{project_id}",
    response={
        200: ProjectImagesGroupedResponse,
        401: Error,
        403: Error,
        404: Error,
    },
    auth=auth,
    tags=["Admin"],
)
def get_admin_project_images(
    request: HttpRequest,
    project_id: UUID,
) -> tuple[int, ProjectImagesGroupedResponse] | tuple[int, dict]:
    if not _is_admin(request.auth):
        return 403, {"detail": "Admin access required"}

    project = get_object_or_404(Project, id=project_id)

    all_images = list(
        ProjectImage.objects.filter(
            project=project,
            upload_status="uploaded",
        ).prefetch_related("variants")
    )

    return 200, ProjectImagesGroupedResponse(
        icon=_slot_for(ImagePurpose.ICON, all_images),
        screenshots=_slot_for(ImagePurpose.SCREENSHOT, all_images),
        main_image=_slot_for(ImagePurpose.MAIN_IMAGE, all_images),
        winner_composite=_slot_for(ImagePurpose.WINNER_COMPOSITE, all_images),
    )
