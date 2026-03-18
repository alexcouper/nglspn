import logging
from typing import Any
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.image_generation import (
    GenerateImageRequest,
    GenerateImageResponse,
    GenerationStatusResponse,
    ProjectImagesGroupedResponse,
    ProposedImageResponse,
    PurposeImageSlot,
)
from api.tasks.leonardo import generate_project_image
from apps.projects.models import (
    ApprovalStatus,
    ImageGenerationRequest,
    ImagePurpose,
    Project,
    ProjectImage,
)
from services.leonardo.django_impl.client import (
    FLUX_KONTEXT_MODEL_ID,
    PHOENIX_MODEL_ID,
)

logger = logging.getLogger(__name__)

router = Router()

MAX_VARIANTS = 4

DIMENSION_PRESETS: dict[str, tuple[int, int, str]] = {
    ImagePurpose.ICON: (1024, 1024, PHOENIX_MODEL_ID),
    ImagePurpose.MAIN_IMAGE: (1024, 768, PHOENIX_MODEL_ID),
    ImagePurpose.WINNER_COMPOSITE: (
        1248,
        704,
        FLUX_KONTEXT_MODEL_ID,
    ),
}


def _is_admin(user: Any) -> bool:
    return user.groups.filter(name="ADMIN").exists() or user.is_superuser


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


@router.post(
    "/generate",
    response={
        200: GenerateImageResponse,
        400: Error,
        401: Error,
        403: Error,
    },
    auth=auth,
    tags=["Images"],
)
def create_generation(
    request: HttpRequest,
    body: GenerateImageRequest,
) -> tuple[int, GenerateImageResponse | dict]:
    project = get_object_or_404(Project, id=body.project_id)

    user = request.auth
    if not (project.owner_id == user.id or _is_admin(user)):
        return 403, {"detail": "Not authorized"}

    if body.purpose not in DIMENSION_PRESETS:
        return 400, {"detail": f"Invalid purpose: {body.purpose}"}

    if not 1 <= body.num_variants <= MAX_VARIANTS:
        return 400, {
            "detail": "num_variants must be between 1 and 4",
        }

    width, height, model_id = DIMENSION_PRESETS[body.purpose]

    reference_image = None
    if body.reference_image_id:
        reference_image = get_object_or_404(
            ProjectImage,
            id=body.reference_image_id,
            project=project,
        )

    gen_request = ImageGenerationRequest.objects.create(
        project=project,
        purpose=body.purpose,
        prompt_text=body.prompt_text,
        device_frame=body.device_frame,
        reference_image=reference_image,
        leonardo_model_id=model_id,
        width=width,
        height=height,
        num_variants=body.num_variants,
        created_by=user,
    )

    generate_project_image.enqueue(str(gen_request.id))

    return 200, GenerateImageResponse(
        generation_request_id=gen_request.id,
    )


@router.get(
    "/generate/{generation_request_id}",
    response={
        200: GenerationStatusResponse,
        401: Error,
        404: Error,
    },
    auth=auth,
    tags=["Images"],
)
def get_generation_status(
    request: HttpRequest,
    generation_request_id: UUID,
) -> tuple[int, GenerationStatusResponse | dict]:
    gen_request = get_object_or_404(
        ImageGenerationRequest.objects.select_related("project"),
        id=generation_request_id,
    )

    user = request.auth
    is_owner = gen_request.project.owner_id == user.id
    if not (is_owner or _is_admin(user)):
        return 404, {"detail": "Not found"}

    images: list[ProposedImageResponse] = []
    if gen_request.status == "completed":
        result_images = ProjectImage.objects.filter(
            generation_request=gen_request,
        ).prefetch_related("variants")
        images = [_image_to_response(img) for img in result_images]

    return 200, GenerationStatusResponse(
        id=gen_request.id,
        status=gen_request.status,
        purpose=gen_request.purpose,
        prompt_text=gen_request.prompt_text,
        error_message=gen_request.error_message,
        images=images,
    )


@router.post(
    "/{image_id}/accept",
    response={
        200: ProposedImageResponse,
        401: Error,
        403: Error,
        404: Error,
    },
    auth=auth,
    tags=["Images"],
)
def accept_image(
    request: HttpRequest,
    image_id: UUID,
) -> tuple[int, ProposedImageResponse | dict]:
    image = get_object_or_404(
        ProjectImage.objects.select_related(
            "project",
        ).prefetch_related("variants"),
        id=image_id,
        approval_status=ApprovalStatus.PROPOSED,
    )

    user = request.auth
    if not (image.project.owner_id == user.id or _is_admin(user)):
        return 403, {"detail": "Not authorized"}

    # Displace previous active image for this purpose
    ProjectImage.objects.filter(
        project=image.project,
        purpose=image.purpose,
        approval_status=ApprovalStatus.ACTIVE,
    ).exclude(purpose=ImagePurpose.SCREENSHOT).update(
        approval_status=ApprovalStatus.PROPOSED,
    )

    image.approval_status = ApprovalStatus.ACTIVE
    image.save(update_fields=["approval_status"])

    return 200, _image_to_response(image)


@router.post(
    "/{image_id}/reject",
    response={200: dict, 401: Error, 403: Error, 404: Error},
    auth=auth,
    tags=["Images"],
)
def reject_image(
    request: HttpRequest,
    image_id: UUID,
) -> tuple[int, dict]:
    image = get_object_or_404(
        ProjectImage.objects.select_related("project"),
        id=image_id,
        approval_status=ApprovalStatus.PROPOSED,
    )

    user = request.auth
    if not (image.project.owner_id == user.id or _is_admin(user)):
        return 403, {"detail": "Not authorized"}

    from services.leonardo.django_impl.handler import (  # noqa: PLC0415
        delete_image_files,
    )

    delete_image_files(image)
    image.delete()

    return 200, {"detail": "Image rejected and deleted"}


@router.get(
    "/project/{project_id}",
    response={
        200: ProjectImagesGroupedResponse,
        401: Error,
        404: Error,
    },
    auth=auth,
    tags=["Images"],
)
def get_project_images(
    request: HttpRequest,
    project_id: UUID,
) -> tuple[int, ProjectImagesGroupedResponse | dict]:
    project = get_object_or_404(Project, id=project_id)

    user = request.auth
    if not (project.owner_id == user.id or _is_admin(user)):
        return 404, {"detail": "Not found"}

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
