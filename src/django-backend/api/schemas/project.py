from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from ninja import Schema

from .tag import TagWithCategoryResponse
from .user import PublicUserProfile


class ProjectCreate(Schema):
    website_url: str
    description: str | None = None
    # fields | None- will be filled by admin during review
    title: str | None = None
    tagline: str | None = None
    long_description: str | None = None
    github_url: str | None = None
    demo_url: str | None = None
    tech_stack: list[str] | None = None
    tag_ids: list[UUID] | None = None
    community_owned: bool = False


class PublishMissingFieldsResponse(Schema):
    detail: str
    missing: list[str]


class ImageVariantResponse(Schema):
    size: str
    url: str
    width: int
    height: int


class ProjectImageResponse(Schema):
    id: UUID
    url: str
    original_filename: str
    content_type: str
    file_size: int
    width: int | None
    height: int | None
    is_main: bool
    is_icon: bool
    is_hero: bool
    is_usage: bool
    display_order: int
    upload_status: str
    created_at: datetime
    variants: list[ImageVariantResponse] = []

    @staticmethod
    def resolve_variants(obj: Any) -> list[Any]:
        return list(obj.variants.all())


class WonCompetitionInfo(Schema):
    name: str
    slug: str


class ContributorSummary(Schema):
    user: PublicUserProfile
    role: Literal["owner", "suggester"]
    full_edit: bool


class ProjectResponse(Schema):
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
    owner: PublicUserProfile
    creator: PublicUserProfile
    contributors: list[ContributorSummary] = []
    tags: list[TagWithCategoryResponse]
    images: list[ProjectImageResponse] = []
    won_competitions: list[WonCompetitionInfo] = []
    community_owned: bool = False

    @staticmethod
    def resolve_owner(obj: Any) -> Any:
        return obj.creator

    @staticmethod
    def resolve_contributors(obj: Any) -> list[Any]:
        return list(obj.contributors.all())

    @staticmethod
    def resolve_images(obj: Any) -> list[Any]:
        return list(obj.images.all())

    @staticmethod
    def resolve_tags(obj: Any) -> list[Any]:
        """Only return non-rejected tags."""
        return list(obj.tags.exclude(status="rejected"))

    @staticmethod
    def resolve_won_competitions(obj: Any) -> list[Any]:
        return list(obj.won_competitions.all())


class PresignedUploadRequest(Schema):
    filename: str
    content_type: str
    file_size: int
    is_icon: bool = False


class PresignedUploadResponse(Schema):
    image_id: UUID
    upload_url: str
    method: str
    headers: dict[str, str]
    storage_key: str


class ImageUploadCompleteRequest(Schema):
    width: int | None = None
    height: int | None = None


class ImageOrderUpdate(Schema):
    image_id: UUID
    display_order: int


class ImageOrderUpdateRequest(Schema):
    images: list[ImageOrderUpdate]


class UpdateImageRolesRequest(Schema):
    is_main: bool | None = None
    is_hero: bool | None = None
    is_usage: bool | None = None


class ProjectListItemResponse(Schema):
    id: UUID
    slug: str | None
    title: str
    tagline: str
    status: str
    created_at: datetime
    tags: list[TagWithCategoryResponse] = []
    won_competitions: list[WonCompetitionInfo] = []
    main_image_url: str | None = None
    main_image_thumb_url: str | None = None

    @classmethod
    def from_list_item(cls, item: Any) -> "ProjectListItemResponse":
        return cls(
            id=item.project.id,
            slug=item.project.slug,
            title=item.project.title,
            tagline=item.project.tagline,
            status=item.project.status,
            created_at=item.project.created_at,
            tags=item.tags,
            won_competitions=list(item.project.won_competitions.all()),
            main_image_url=item.main_image_url,
            main_image_thumb_url=item.main_image_thumb_url,
        )


class ProjectListResponse(Schema):
    projects: list[ProjectListItemResponse]
    total: int
    page: int
    per_page: int
    pages: int
    pending_projects_count: int


class DiscoverProjectResponse(Schema):
    id: UUID
    slug: str | None
    title: str
    tagline: str
    icon_url: str | None = None
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    category_name: str | None = None
    category_slug: str | None = None
    discussion_count: int = 0
    won_competitions: list[WonCompetitionInfo] = []
    community_owned: bool = False

    @classmethod
    def from_discover_item(cls, item: Any) -> "DiscoverProjectResponse":
        return cls(
            id=item.project.id,
            slug=item.project.slug,
            title=item.project.title,
            tagline=item.project.tagline,
            icon_url=item.icon_url,
            hero_banner_url=item.hero_banner_url,
            in_use_image_url=item.in_use_image_url,
            category_name=item.category_name,
            category_slug=item.category_slug,
            discussion_count=item.discussion_count,
            won_competitions=list(item.project.won_competitions.all()),
            community_owned=getattr(item.project, "community_owned", False),
        )


class CategoryResponse(Schema):
    id: UUID
    name: str
    slug: str
    project_count: int


class WinnerProjectResponse(Schema):
    id: UUID
    slug: str | None
    title: str
    tagline: str
    icon_url: str | None = None
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    competition_name: str
    competition_slug: str
    competition_submission_deadline: str


class AdminProjectResponse(ProjectResponse):
    rejection_reason: str | None
    approved_by: PublicUserProfile | None
    submission_month: str


class ProjectApproval(Schema):
    approved: bool
    rejection_reason: str | None = None
