from datetime import datetime
from uuid import UUID

from ninja import Schema

from api.schemas.project import ImageVariantResponse


class GenerateImageRequest(Schema):
    project_id: UUID
    purpose: str  # icon, main_image, winner_composite
    prompt_text: str
    device_frame: str | None = None  # mobile, laptop, watch
    reference_image_id: UUID | None = None
    num_variants: int = 1


class GenerateImageResponse(Schema):
    generation_request_id: UUID


class GenerationStatusResponse(Schema):
    id: UUID
    status: str
    purpose: str
    prompt_text: str
    error_message: str | None = None
    images: list["ProposedImageResponse"] = []


class ProposedImageResponse(Schema):
    id: UUID
    url: str
    width: int | None
    height: int | None
    variants: list[ImageVariantResponse] = []


class PurposeImageSlot(Schema):
    active: list[ProposedImageResponse] = []
    proposed: list[ProposedImageResponse] = []


class ProjectImagesGroupedResponse(Schema):
    icon: PurposeImageSlot
    screenshots: PurposeImageSlot
    main_image: PurposeImageSlot
    winner_composite: PurposeImageSlot


class ImageCompleteness(Schema):
    icon: str  # active, proposed, missing
    main_image: str
    winner_composite: str | None  # null if not a winner


class AdminProjectListItem(Schema):
    id: UUID
    title: str
    owner_email: str
    image_completeness: ImageCompleteness
    created_at: datetime


class AdminProjectListResponse(Schema):
    projects: list[AdminProjectListItem]
    total: int
