from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from ninja import Schema

from api.schemas.project import (
    ContributorSummary,
    ImageVariantResponse,
    ProjectImageResponse,
    WonCompetitionInfo,
)
from api.schemas.tag import TagWithCategoryResponse
from api.schemas.user import UserResponse


class ReviewStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED = "ended"


class ReviewCompetitionResponse(Schema):
    """Competition that the current user is assigned to review."""

    id: UUID
    name: str
    start_date: date
    submission_deadline: date
    image_url: str | None = None
    project_count: int
    my_review_status: ReviewStatusEnum


class ReviewCompetitionListResponse(Schema):
    competitions: list[ReviewCompetitionResponse]


class ReviewProjectResponse(Schema):
    """Project within a competition being reviewed, with ranking info."""

    id: UUID
    slug: str | None = None
    title: str
    tagline: str = ""
    description: str
    website_url: str
    main_image_url: str | None = None
    main_image_variants: list[ImageVariantResponse] = []
    # Resolved the same way the listing endpoints resolve them, so the ballot
    # card and the listing card show the same project.
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    category_name: str | None = None
    my_ranking: int | None = None


class ReviewCompetitionDetailResponse(Schema):
    """Competition detail split into the reviewer's ballot and what is left.

    `ranked_projects` is in the reviewer's saved order; `pool_projects` is in an
    order stable for this reviewer and uncorrelated with any other reviewer's.
    The client renders both as given rather than deriving an order of its own.
    """

    id: UUID
    name: str
    start_date: date
    submission_deadline: date
    my_review_status: ReviewStatusEnum
    ranked_projects: list[ReviewProjectResponse]
    pool_projects: list[ReviewProjectResponse]


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
    slug: str | None
    title: str
    tagline: str
    description: str
    long_description: str | None
    website_url: str
    github_url: str | None
    demo_url: str | None
    tech_stack: list[str]
    status: str
    created_at: datetime
    approved_at: datetime | None
    published_at: datetime | None
    # `owner` is a transitional shim populated from `creator` so existing
    # frontend consumers keep working until they migrate. To be removed in a
    # follow-up change after the FE consumes `creator` directly.
    owner: UserResponse
    creator: UserResponse
    contributors: list[ContributorSummary] = []
    tags: list[TagWithCategoryResponse]
    images: list[ProjectImageResponse] = []
    won_competitions: list[WonCompetitionInfo] = []
    is_community_tipoff: bool = False
    is_followed: bool = False

    @staticmethod
    def resolve_owner(obj: Any) -> Any:
        return obj.creator

    @staticmethod
    def resolve_contributors(obj: Any) -> list[Any]:
        return list(obj.contributors.all())

    @staticmethod
    def resolve_images(obj: Any) -> list[Any]:
        """Return uploaded images. Uses prefetch cache when available."""
        return list(obj.images.all())

    @staticmethod
    def resolve_won_competitions(obj: Any) -> list[Any]:
        return list(obj.won_competitions.all())
