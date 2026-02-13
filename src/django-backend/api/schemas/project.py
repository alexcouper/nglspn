from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from .tag import TagWithCategoryResponse
from .user import PublicUserProfile


class ProjectCreate(Schema):
    website_url: str
    description: str | None = None
    # fields | None- will be filled by admin during review
    title: str | None = None
    long_description: str | None = None
    github_url: str | None = None
    demo_url: str | None = None
    tech_stack: list[str] | None = None
    tag_ids: list[UUID] | None = None
    competition_id: UUID | None = None


class ProjectImageResponse(Schema):
    """Response schema for project images."""

    id: UUID
    url: str
    original_filename: str
    content_type: str
    file_size: int
    width: int | None
    height: int | None
    is_main: bool
    display_order: int
    upload_status: str
    created_at: datetime


class WonCompetitionInfo(Schema):
    name: str
    slug: str


class ProjectResponse(Schema):
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
    owner: PublicUserProfile
    tags: list[TagWithCategoryResponse]
    images: list[ProjectImageResponse] = []
    won_competitions: list[WonCompetitionInfo] = []

    @staticmethod
    def resolve_images(obj: Any) -> list[Any]:
        """Only return uploaded images."""
        return list(obj.images.filter(upload_status="uploaded"))

    @staticmethod
    def resolve_tags(obj: Any) -> list[Any]:
        """Only return non-rejected tags."""
        return list(obj.tags.exclude(status="rejected"))

    @staticmethod
    def resolve_won_competitions(obj: Any) -> list[Any]:
        return list(obj.won_competitions.all())


class PresignedUploadRequest(Schema):
    """Request schema for generating presigned upload URL."""

    filename: str
    content_type: str
    file_size: int


class PresignedUploadResponse(Schema):
    """Response with presigned upload URL."""

    image_id: UUID
    upload_url: str
    method: str
    headers: dict[str, str]
    storage_key: str


class ImageUploadCompleteRequest(Schema):
    """Request to confirm upload completion."""

    width: int | None = None
    height: int | None = None


class ImageOrderUpdate(Schema):
    """Schema for updating a single image's order."""

    image_id: UUID
    display_order: int


class ImageOrderUpdateRequest(Schema):
    """Request to update image order."""

    images: list[ImageOrderUpdate]


class SetMainImageRequest(Schema):
    """Request to set main image."""

    image_id: UUID


class ProjectListResponse(Schema):
    projects: list[ProjectResponse]
    total: int
    page: int
    per_page: int
    pages: int
    pending_projects_count: int


class AdminProjectResponse(ProjectResponse):
    rejection_reason: str | None
    approved_by: PublicUserProfile | None
    submission_month: str


class ProjectApproval(Schema):
    approved: bool
    rejection_reason: str | None = None
    is_featured: bool = False
