from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from services.articles.summary import derive_summary

from .project import ImageResponse
from .user import PublicUserProfile


class CropRect(Schema):
    """A crop rectangle normalised 0-1 against the source image."""

    x: float
    y: float
    w: float
    h: float
    # The rendered aspect as a decimal. Derivable from the rect plus the source
    # dimensions, but carried explicitly so a listing card can reserve its box
    # without being told the source's pixel size.
    ratio: float


class ArticleCreate(Schema):
    channel_id: UUID
    title: str = ""
    body: str = ""
    # No listing image here: an image is uploaded against an article, so a brand
    # new article cannot have one yet. The editor creates the draft first and
    # sets the listing image by PATCH.


class OwnArticleCreate(Schema):
    """`ArticleCreate` without the channel: an author-owned article has none."""

    title: str = ""
    body: str = ""


class ArticleUpdate(Schema):
    title: str | None = None
    body: str | None = None
    # "" is meaningful here: it clears the override and returns the article to
    # the derived fallback.
    summary: str | None = None
    # The cover. null is meaningful on both of these, so patch_article reads
    # them out of dict(exclude_unset=True) rather than treating null as "not
    # sent": null on listing_image_id removes the cover, and null on
    # listing_crop drops back to the 16:9 centred default.
    listing_image_id: UUID | None = None
    listing_crop: CropRect | None = None
    channel_id: UUID | None = None
    published_at: datetime | None = None


class ArticlePublish(Schema):
    published_at: datetime | None = None


class ArticleImageUploadRequest(Schema):
    """An article upload names only the file.

    The article it belongs to is in the path, so there is no `source` /
    `source_id` pair here that could disagree with which article the row is
    stored against.
    """

    filename: str
    content_type: str
    file_size: int


class ArticleProjectRef(Schema):
    id: UUID
    slug: str | None
    title: str


class ArticleChannelRef(Schema):
    id: UUID
    name: str


class ArticleOut(Schema):
    id: UUID
    # Both null on an author-owned article: no project, and no channel until
    # publish attaches the author's personal one. `author` carries the owner.
    project: ArticleProjectRef | None
    channel: ArticleChannelRef | None
    author: PublicUserProfile | None
    title: str
    body: str
    # `summary` is the stored override (so the editor knows whether one exists);
    # `summary_display` is what a listing will actually show.
    summary: str
    summary_display: str
    listing_image_id: UUID | None
    listing_image_url: str | None
    listing_crop: CropRect | None
    # The full image, with variants. The editor needs this: article images are
    # excluded from `ProjectResponse.images`, so it cannot look the listing
    # image up there when loading an article for editing.
    listing_image: ImageResponse | None
    # Every image uploaded for this article. This is the listing-image wizard's
    # selection list — it comes off the image-article link, so no second
    # endpoint and no parsing of the body are needed for it.
    images: list[ImageResponse]
    slug: str | None
    source: str
    external_url: str | None
    state: str
    published_at: datetime | None
    global_visibility: str
    is_globally_visible: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_project(obj: Any) -> dict[str, Any] | None:
        project = obj.project
        if project is None:
            return None
        return {"id": project.id, "slug": project.slug, "title": project.title}

    @staticmethod
    def resolve_channel(obj: Any) -> dict[str, Any] | None:
        channel = obj.channel
        if channel is None:
            return None
        return {"id": channel.id, "name": channel.name}

    @staticmethod
    def resolve_summary_display(obj: Any) -> str:
        return obj.summary or derive_summary(obj.body)

    @staticmethod
    def resolve_listing_image_id(obj: Any) -> UUID | None:
        return obj.listing_image_id

    @staticmethod
    def resolve_listing_image_url(obj: Any) -> str | None:
        image = obj.listing_image
        if image is None:
            return None
        return image.url

    @staticmethod
    def resolve_listing_image(obj: Any) -> Any:
        return obj.listing_image

    @staticmethod
    def resolve_images(obj: Any) -> list[Any]:
        # Only completed uploads: a `PENDING` row whose PUT failed has a
        # storage key but no object behind it, so offering it to the wizard
        # would let an author pick a listing image that renders as a broken
        # card. Ordered by upload time to match how `auto` picks its image, so
        # the wizard lists them in the same order the default was chosen from.
        # Filtered in Python so a prefetched relation is not thrown away.
        return sorted(
            (img for img in obj.images.all() if img.is_uploaded),
            key=lambda img: img.created_at,
        )

    @staticmethod
    def resolve_is_globally_visible(obj: Any) -> bool:
        return obj.is_globally_visible


class ArticleListItem(Schema):
    id: UUID
    title: str
    summary: str
    slug: str | None
    state: str
    published_at: datetime | None
    global_visibility: str
    # Derived rather than left to the client: only an editor's listing carries
    # invisible rows at all, and the rule for which ones those are belongs on one
    # side of the wire.
    is_globally_visible: bool
    channel: ArticleChannelRef | None
    listing_image_url: str | None
    listing_crop: CropRect | None

    @staticmethod
    def resolve_channel(obj: Any) -> dict[str, Any] | None:
        return ArticleOut.resolve_channel(obj)

    @staticmethod
    def resolve_is_globally_visible(obj: Any) -> bool:
        return obj.is_globally_visible

    # REPO.articles.for_project selects whole rows, so obj.body is already
    # loaded and this costs no extra queries. Do not add .only(...) to that
    # queryset without including body.
    @staticmethod
    def resolve_summary(obj: Any) -> str:
        return obj.summary or derive_summary(obj.body)

    @staticmethod
    def resolve_listing_image_url(obj: Any) -> str | None:
        image = obj.listing_image
        if image is None:
            return None
        return image.url


class UserArticleResponse(Schema):
    """One entry in a user's public article list.

    The public half of `ArticleListItem` plus the project, because a project
    article's URL lives under its project and the profile shows articles from
    many. `project` is null for an author-owned article, whose URL is under the
    profile itself. No visibility fields: everything the list returns is
    published and visible.
    """

    id: UUID
    title: str
    summary: str
    slug: str | None
    published_at: datetime | None
    channel: ArticleChannelRef | None
    project: ArticleProjectRef | None
    listing_image_url: str | None
    listing_crop: CropRect | None

    @staticmethod
    def resolve_channel(obj: Any) -> dict[str, Any] | None:
        return ArticleOut.resolve_channel(obj)

    @staticmethod
    def resolve_project(obj: Any) -> dict[str, Any] | None:
        return ArticleOut.resolve_project(obj)

    @staticmethod
    def resolve_summary(obj: Any) -> str:
        return ArticleListItem.resolve_summary(obj)

    @staticmethod
    def resolve_listing_image_url(obj: Any) -> str | None:
        return ArticleListItem.resolve_listing_image_url(obj)


class OwnArticleResponse(UserArticleResponse):
    """One entry in the owner's own article list: everything they wrote, in
    every state, with what the my-projects badges need."""

    state: str
    global_visibility: str
    is_globally_visible: bool

    @staticmethod
    def resolve_is_globally_visible(obj: Any) -> bool:
        return obj.is_globally_visible
