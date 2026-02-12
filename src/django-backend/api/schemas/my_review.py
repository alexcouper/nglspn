from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from ninja import Schema

from api.schemas.project import ProjectImageResponse
from api.schemas.tag import TagWithCategoryResponse
from api.schemas.user import UserResponse


class ReviewStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ReviewCompetitionResponse(Schema):
    """Competition that the current user is assigned to review."""

    id: UUID
    name: str
    start_date: date
    end_date: date
    image_url: str | None = None
    project_count: int
    my_review_status: ReviewStatusEnum


class ReviewCompetitionListResponse(Schema):
    competitions: list[ReviewCompetitionResponse]


class ReviewProjectResponse(Schema):
    """Project within a competition being reviewed, with ranking info."""

    id: UUID
    title: str
    description: str
    website_url: str
    main_image_url: str | None = None
    my_ranking: int | None = None

    @staticmethod
    def resolve_main_image_url(obj: Any) -> str | None:
        main_image = obj.images.filter(upload_status="uploaded", is_main=True).first()
        if not main_image:
            main_image = obj.images.filter(upload_status="uploaded").first()
        return main_image.url if main_image else None


class ReviewCompetitionDetailResponse(Schema):
    """Competition detail with projects and reviewer's rankings."""

    id: UUID
    name: str
    start_date: date
    end_date: date
    my_review_status: ReviewStatusEnum
    projects: list[ReviewProjectResponse]


class RankingUpdateRequest(Schema):
    """Request to update rankings for a competition."""

    project_ids: list[UUID]


class StatusUpdateRequest(Schema):
    """Request to update the reviewer's status for a competition."""

    status: ReviewStatusEnum


class SuccessResponse(Schema):
    """Simple success response."""

    success: bool = True


class ReviewProjectDetailResponse(Schema):
    """Full project details for a reviewer."""

    id: UUID
    title: str
    description: str
    long_description: str | None
    website_url: str
    github_url: str | None
    demo_url: str | None
    tech_stack: list[str]
    monthly_visitors: int
    status: str
    is_featured: bool
    created_at: datetime
    approved_at: datetime | None
    owner: UserResponse
    tags: list[TagWithCategoryResponse]
    images: list[ProjectImageResponse] = []

    @staticmethod
    def resolve_images(obj: Any) -> list[Any]:
        """Only return uploaded images."""
        return list(obj.images.filter(upload_status="uploaded"))
